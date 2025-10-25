"""Game state representation and transitions."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

from .cards import Card, Deck
from .hand_eval import rank_hand
from .players import BasePlayer
from .pot import SidePotManager
from .rules import BlindStructure, posting_order, rotate_button


class Street(Enum):
    PREFLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    SHOWDOWN = auto()


@dataclass
class PlayerAction:
    seat: int
    move: str
    amount: int = 0


@dataclass
class TableState:
    """Mutable state for a Hold'em table."""

    players: List[BasePlayer]
    blind_structure: BlindStructure
    deck: Deck = field(default_factory=Deck)
    dealer_index: int = 0
    board: List[Card] = field(default_factory=list)
    pot_manager: SidePotManager = field(default_factory=SidePotManager)
    street: Street = Street.PREFLOP
    action_log: List[PlayerAction] = field(default_factory=list)
    current_bets: Dict[int, int] = field(default_factory=dict)
    last_raise: int = 0
    current_bettor: Optional[int] = None
    burned_cards: List[Card] = field(default_factory=list)

    def reset_for_new_hand(self) -> None:
        """Prepare for the next hand."""

        self.board.clear()
        self.burned_cards.clear()
        self.pot_manager.reset()
        self.deck.reset()
        self.street = Street.PREFLOP
        self.action_log.clear()
        self.current_bets.clear()
        self.last_raise = self.blind_structure.big_blind
        self.current_bettor = None
        for player in self.players:
            player.hole_cards = ()
            player.sitting_out = False

    def active_players(self) -> List[BasePlayer]:
        return [p for p in self.players if p.stack > 0 and not p.sitting_out]

    def rotate_button(self) -> None:
        self.dealer_index = rotate_button(len(self.players), self.dealer_index)

    def deal_hole_cards(self) -> None:
        for _ in range(2):
            for player in self.active_players():
                player.hole_cards = tuple(player.hole_cards) + tuple(self.deck.deal(1))

    def post_blinds(self) -> None:
        order = list(posting_order(len(self.players), self.dealer_index))
        for seat in order:
            player = self.players[seat]
            if self.blind_structure.ante:
                ante = min(player.stack, self.blind_structure.ante)
                if ante:
                    player.bet(ante)
                    self.pot_manager.add_bet(seat, ante)
        if len(order) >= 1:
            sb = self.players[order[0]]
            sb_amount = min(sb.stack, self.blind_structure.small_blind)
            sb.bet(sb_amount)
            self.current_bets[order[0]] = sb_amount
            self.pot_manager.add_bet(order[0], sb_amount)
        if len(order) >= 2:
            bb = self.players[order[1]]
            bb_amount = min(bb.stack, self.blind_structure.big_blind)
            bb.bet(bb_amount)
            self.current_bets[order[1]] = bb_amount
            self.pot_manager.add_bet(order[1], bb_amount)
            self.last_raise = bb_amount - self.blind_structure.small_blind
            self.current_bettor = (order[1] + 1) % len(self.players)

    def move_to_next_street(self) -> None:
        if self.street == Street.PREFLOP:
            self._deal_flop()
        elif self.street == Street.FLOP:
            self._deal_turn()
        elif self.street == Street.TURN:
            self._deal_river()
        elif self.street == Street.RIVER:
            self.street = Street.SHOWDOWN
        self.current_bets.clear()
        self.last_raise = 0

    def _deal_flop(self) -> None:
        self._burn()
        self.board.extend(self.deck.deal(3))
        self.street = Street.FLOP

    def _deal_turn(self) -> None:
        self._burn()
        self.board.extend(self.deck.deal(1))
        self.street = Street.TURN

    def _deal_river(self) -> None:
        self._burn()
        self.board.extend(self.deck.deal(1))
        self.street = Street.RIVER

    def resolve_showdown(self) -> List[tuple[int, int]]:
        """Determine winners and pay out side pots."""

        pots = self.pot_manager.build([player.seat for player in self.active_players()])
        winnings: List[tuple[int, int]] = []
        if not pots:
            return winnings
        for pot in pots:
            contenders = [self.players[seat] for seat in pot.eligible_seats if not self.players[seat].sitting_out]
            if not contenders:
                continue
            best = None
            winners: List[BasePlayer] = []
            for player in contenders:
                cards = getattr(player, 'hole_cards', tuple())
                if len(cards) < 2:
                    continue
                score = rank_hand(tuple(cards) + tuple(self.board))
                key = (score[0], score[1])
                if best is None or key > best:
                    best = key
                    winners = [player]
                elif key == best:
                    winners.append(player)
            if not winners:
                continue
            share = pot.amount // len(winners)
            remainder = pot.amount - share * len(winners)
            for idx, winner in enumerate(winners):
                win_amount = share + (1 if idx < remainder else 0)
                winner.add_winnings(win_amount)
                winnings.append((winner.seat, win_amount))
        self.street = Street.SHOWDOWN
        return winnings

    def _burn(self) -> None:
        card = self.deck.deal(1)[0]
        self.burned_cards.append(card)


__all__ = ["TableState", "Street", "PlayerAction"]
