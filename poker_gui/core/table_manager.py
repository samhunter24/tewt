"""High level table manager orchestration."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from .ai import DecisionEngine
from .game import PlayerAction, Street, TableState
from .players import AIPlayer, BasePlayer, HumanPlayer
from .rules import BlindStructure

DATA_PATH = Path(__file__).resolve().parent.parent / "data"


@dataclass
class TableConfig:
    name: str = "Main Table"
    seats: int = 6
    starting_stack: int = 200
    blinds: BlindStructure = field(default_factory=lambda: BlindStructure(1, 2, 0))
    tournament: bool = False


class TableManager:
    """Coordinates the table state and turn progression."""

    def __init__(self, config: TableConfig) -> None:
        self.config = config
        self.state = TableState(players=[], blind_structure=config.blinds)
        self.decision_engine = DecisionEngine()
        self.hand_number = 0
        self._load_default_players()

    def _load_default_players(self) -> None:
        default_players_path = DATA_PATH / "default_players.json"
        if default_players_path.exists():
            profile_data = json.loads(default_players_path.read_text())
        else:
            profile_data = {
                "seats": [
                    {"type": "human", "name": "You"},
                    {"type": "ai", "name": "Ava", "profile": "Casual"},
                    {"type": "ai", "name": "Blake", "profile": "Solid"},
                ]
            }
        for seat in range(self.config.seats):
            if seat < len(profile_data["seats"]):
                entry = profile_data["seats"][seat]
            else:
                entry = {"type": "ai", "name": f"Bot {seat+1}", "profile": "Casual"}
            if entry["type"] == "human":
                player = HumanPlayer(seat=seat, name=entry["name"], stack=self.config.starting_stack)
            else:
                player = AIPlayer(
                    seat=seat,
                    name=entry["name"],
                    stack=self.config.starting_stack,
                    strategy=entry.get("profile"),
                )
            self.state.players.append(player)

    def start_hand(self) -> None:
        self.state.rotate_button()
        self.state.reset_for_new_hand()
        self.state.deal_hole_cards()
        self.state.post_blinds()
        self.hand_number += 1

    def legal_moves(self, seat: int) -> List[Tuple[str, int, int]]:
        player = self.state.players[seat]
        contributed = self.state.current_bets.get(seat, 0)
        current_max = max(self.state.current_bets.values(), default=0)
        to_call = max(0, current_max - contributed)
        stack = player.stack
        moves: List[Tuple[str, int, int]] = [("fold", contributed, contributed)]
        if to_call <= 0:
            moves.append(("check", contributed, contributed))
        else:
            call_total = contributed + min(to_call, stack)
            moves.append(("call", call_total, call_total))
        remaining = stack - to_call
        if remaining > 0:
            min_raise = self.state.last_raise or self.state.blind_structure.big_blind
            raise_to = contributed + to_call + min_raise
            max_total = contributed + stack
            if raise_to < max_total:
                moves.append(("raise", raise_to, max_total))
            else:
                moves.append(("raise", max_total, max_total))
        elif to_call == 0 and stack > 0:
            min_bet = self.state.blind_structure.big_blind
            bet_to = contributed + min(min_bet, stack)
            moves.append(("bet", bet_to, contributed + stack))
        return moves

    def _apply_bet(self, seat: int, amount: int) -> int:
        contributed = self.state.current_bets.get(seat, 0)
        to_contribute = max(0, amount - contributed)
        if to_contribute:
            player = self.state.players[seat]
            player.bet(to_contribute)
            self.state.pot_manager.add_bet(seat, to_contribute)
            self.state.current_bets[seat] = contributed + to_contribute
        return to_contribute

    def apply_action(self, seat: int, move: str, amount: int = 0) -> None:
        move = move.lower()
        if move in {"call", "bet", "raise"}:
            contributed = self._apply_bet(seat, amount)
            if move in {"bet", "raise"} and contributed > 0:
                self.state.last_raise = contributed
        elif move == "fold":
            amount = 0
            self.state.players[seat].sitting_out = True
        elif move == "check":
            amount = 0
        self.state.action_log.append(PlayerAction(seat=seat, move=move, amount=amount))

    def play_ai_turn(self, seat: int) -> PlayerAction:
        player = self.state.players[seat]
        legal = self.legal_moves(seat)
        legal_map = {move: (min_amount, max_amount) for move, min_amount, max_amount in legal}
        hole_cards = tuple(getattr(player, "hole_cards", ()))
        if self.state.street == Street.PREFLOP:
            decision = self.decision_engine.choose_preflop(player, self._position_for_seat(seat), hole_cards, legal)
        else:
            decision = self.decision_engine.choose_postflop(player, hole_cards, self.state.board, legal)
        if decision.move not in legal_map:
            decision.move = "fold"
            decision.amount = 0
        elif decision.amount is None:
            decision.amount = legal_map.get(decision.move, (0, 0))[0]
        self.apply_action(seat, decision.move, decision.amount)
        return PlayerAction(seat=seat, move=decision.move, amount=decision.amount)

    def _position_for_seat(self, seat: int) -> str:
        offset = (seat - self.state.dealer_index) % len(self.state.players)
        if offset == 0:
            return "BTN"
        if offset == 1:
            return "SB"
        if offset == 2:
            return "BB"
        if offset <= 4:
            return "MP"
        return "CO"


def create_default_table() -> TableManager:
    return TableManager(TableConfig())


__all__ = ["TableManager", "TableConfig", "create_default_table"]
