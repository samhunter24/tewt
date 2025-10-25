"""Monte Carlo equity simulation."""
from __future__ import annotations

import random
from typing import Sequence, Tuple

from .cards import Card, Deck
from .hand_eval import compare_hands


class EquityEstimator:
    def __init__(self, *, rng: random.Random | None = None, samples: int = 300) -> None:
        self.rng = rng or random.Random()
        self.samples = samples

    def estimate_equity(self, hole_cards: Tuple[Card, Card], community: Sequence[Card]) -> float:
        """Estimate hero equity against one random opponent."""

        wins = 0
        ties = 0
        total = 0
        for _ in range(self.samples):
            deck = Deck(rng=self.rng)
            deck.remove_cards(list(hole_cards) + list(community))
            deck.shuffle()
            opp_cards = deck.deal(2)
            missing = 5 - len(community)
            board = list(community) + deck.deal(missing)
            result = compare_hands(hole_cards + tuple(board), opp_cards + tuple(board))
            total += 1
            if result > 0:
                wins += 1
            elif result == 0:
                ties += 1
        if total == 0:
            return 0.0
        return (wins + ties * 0.5) / total


__all__ = ["EquityEstimator"]
