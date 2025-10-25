"""Simple AI engine for automated opponents."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .cards import Card
from .players import AIPlayer
from .sim import EquityEstimator

DATA_PATH = Path(__file__).resolve().parent.parent / "data"


@dataclass
class ActionDecision:
    move: str
    amount: int | None = None
    info: str | None = None


class PreflopRangeBook:
    """Loads preflop ranges from JSON charts."""

    def __init__(self, filename: str = "ranges.json") -> None:
        self.filename = filename
        self.ranges: Dict[str, Dict[str, float]] = {}
        self.load()

    def load(self) -> None:
        path = DATA_PATH / self.filename
        if path.exists():
            self.ranges = json.loads(path.read_text())
        else:
            self.ranges = {
                "Casual": {"default": 0.4},
                "Solid": {"default": 0.25},
            }

    def should_play(self, profile: str, position: str, hand_key: str) -> bool:
        table = self.ranges.get(profile, self.ranges["Casual"])
        threshold = table.get(position, table.get("default", 0.3))
        strength = table.get(hand_key, threshold)
        return random.random() <= strength


class PostflopPolicy:
    """Stochastic policy based on equity buckets."""

    def __init__(self, *, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

    def choose_action(
        self,
        player: AIPlayer,
        equities: Dict[str, float],
        legal_moves: Iterable[Tuple[str, int, int]],
    ) -> ActionDecision:
        best_action = None
        best_score = -1.0
        for move, min_amount, max_amount in legal_moves:
            equity = equities.get("call", 0.5)
            score = equity
            if move in {"raise", "bet"}:
                score += equities.get("aggression", 0.0)
            score += self.rng.random() * 0.05
            if score > best_score:
                best_score = score
                if move in {"raise", "bet"} and max_amount > min_amount:
                    span = max_amount - min_amount
                    amount = min_amount + int(span * 0.6)
                else:
                    amount = min_amount
                best_action = ActionDecision(move=move, amount=amount)
        return best_action or ActionDecision("check")


class OpponentModel:
    """Tracks opponent tendencies."""

    def __init__(self) -> None:
        self.tendencies: Dict[int, Dict[str, float]] = {}

    def observe(self, seat: int, metric: str, value: float) -> None:
        metrics = self.tendencies.setdefault(seat, {})
        metrics[metric] = value

    def aggression_factor(self, seat: int) -> float:
        metrics = self.tendencies.get(seat, {})
        return metrics.get("aggression", 1.0)


class DecisionEngine:
    """Top-level decision maker for AI players."""

    def __init__(self, *, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.range_book = PreflopRangeBook()
        self.postflop = PostflopPolicy(rng=self.rng)
        self.equity = EquityEstimator(rng=self.rng)
        self.opp_model = OpponentModel()

    def choose_preflop(
        self,
        player: AIPlayer,
        position: str,
        hole_cards: Tuple[Card, Card],
        legal_moves: Iterable[Tuple[str, int, int]],
    ) -> ActionDecision:
        ranks = sorted([card.rank for card in hole_cards], reverse=True)
        suited = hole_cards[0].suit == hole_cards[1].suit
        if ranks[0] == ranks[1]:
            hand_key = f"{ranks[0]}{ranks[1]}"
        else:
            hand_key = f"{ranks[0]}{'s' if suited else 'o'}{ranks[1]}"
        if not self.range_book.should_play(player.profile or "Casual", position, hand_key):
            return ActionDecision("fold")
        return self.postflop.choose_action(player, {"call": 0.55}, legal_moves)

    def choose_postflop(
        self,
        player: AIPlayer,
        hole_cards: Tuple[Card, Card],
        community: Iterable[Card],
        legal_moves: Iterable[Tuple[str, int, int]],
    ) -> ActionDecision:
        equity = self.equity.estimate_equity(hole_cards, list(community))
        equities = {"call": equity, "aggression": max(0.0, equity - 0.5)}
        decision = self.postflop.choose_action(player, equities, legal_moves)
        decision.info = f"Equity={equity:.2f}"
        return decision


__all__ = [
    "DecisionEngine",
    "ActionDecision",
    "PreflopRangeBook",
    "PostflopPolicy",
    "OpponentModel",
]
