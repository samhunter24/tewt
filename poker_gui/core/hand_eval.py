"""Hand evaluation utilities for Texas Hold'em."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Sequence, Tuple

from .cards import Card, VALUE_TO_RANK

HAND_RANKS = {
    8: "Straight Flush",
    7: "Four of a Kind",
    6: "Full House",
    5: "Flush",
    4: "Straight",
    3: "Three of a Kind",
    2: "Two Pair",
    1: "Pair",
    0: "High Card",
}


@dataclass(frozen=True)
class HandRank:
    """Comparable representation of a poker hand rank."""

    category: int
    tiebreaker: Tuple[int, ...]

    def __lt__(self, other: "HandRank") -> bool:
        return (self.category, self.tiebreaker) < (other.category, other.tiebreaker)

    def describe(self) -> str:
        description = HAND_RANKS[self.category]
        if not self.tiebreaker:
            return description
        primary = VALUE_TO_RANK[self.tiebreaker[0]]
        if self.category == 8:
            ranks = "-".join(VALUE_TO_RANK[v] for v in self.tiebreaker)
            return f"Straight Flush ({ranks})"
        if self.category == 7:
            return f"Four of a Kind ({primary}s)"
        if self.category == 6:
            return f"Full House ({VALUE_TO_RANK[self.tiebreaker[0]]}s over {VALUE_TO_RANK[self.tiebreaker[3]]}s)"
        if self.category == 5:
            ranks = " ".join(VALUE_TO_RANK[v] for v in self.tiebreaker)
            return f"Flush ({ranks})"
        if self.category == 4:
            ranks = "-".join(VALUE_TO_RANK[v] for v in self.tiebreaker)
            return f"Straight ({ranks})"
        if self.category == 3:
            return f"Trips {primary}s"
        if self.category == 2:
            return (
                f"Two Pair ({VALUE_TO_RANK[self.tiebreaker[0]]}{VALUE_TO_RANK[self.tiebreaker[1]]}"
                f" with {VALUE_TO_RANK[self.tiebreaker[2]]} kicker)"
            )
        if self.category == 1:
            kickers = " ".join(VALUE_TO_RANK[v] for v in self.tiebreaker[1:])
            return f"Pair of {primary}s ({kickers} kickers)"
        kickers = " ".join(VALUE_TO_RANK[v] for v in self.tiebreaker)
        return f"High Card {kickers}"


def rank_hand(cards: Sequence[Card]) -> Tuple[int, int, str]:
    """Rank the best 5-card hand from the supplied cards."""

    if len(cards) < 5:
        raise ValueError("At least five cards are required")
    best = max((_rank_five(combo) for combo in combinations(cards, 5)))
    description = best.describe()
    return best.category, _encode_tiebreak(best.tiebreaker), description


def _rank_five(cards: Sequence[Card]) -> HandRank:
    ranks = sorted((card.rank for card in cards), reverse=True)
    suits = [card.suit for card in cards]
    rank_counts = Counter(ranks)

    is_flush = len(set(suits)) == 1
    straight_high = _straight_high(ranks)
    if is_flush and straight_high is not None:
        return HandRank(8, _straight_sequence(straight_high))

    counts = sorted(rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

    if counts[0][1] == 4:
        kicker = next(rank for rank in ranks if rank != counts[0][0])
        return HandRank(7, (counts[0][0], counts[0][0], counts[0][0], counts[0][0], kicker))

    if counts[0][1] == 3 and len(counts) > 1 and counts[1][1] == 2:
        return HandRank(6, (counts[0][0], counts[0][0], counts[0][0], counts[1][0], counts[1][0]))

    if is_flush:
        return HandRank(5, tuple(ranks))

    if straight_high is not None:
        return HandRank(4, _straight_sequence(straight_high))

    if counts[0][1] == 3:
        kickers = tuple(rank for rank in ranks if rank != counts[0][0])
        return HandRank(3, (counts[0][0], counts[0][0], counts[0][0]) + kickers)

    if counts[0][1] == 2 and len(counts) > 1 and counts[1][1] == 2:
        pair_ranks = sorted((counts[0][0], counts[1][0]), reverse=True)
        kicker = next(rank for rank in ranks if rank not in pair_ranks)
        return HandRank(2, (pair_ranks[0], pair_ranks[1], kicker))

    if counts[0][1] == 2:
        kickers = tuple(rank for rank in ranks if rank != counts[0][0])
        return HandRank(1, (counts[0][0],) + kickers)

    return HandRank(0, tuple(ranks))


def _straight_high(ranks: Iterable[int]) -> int | None:
    unique = sorted(set(ranks), reverse=True)
    if 14 in unique:
        unique.append(1)
    for idx in range(len(unique) - 4):
        window = unique[idx : idx + 5]
        if window[0] - window[4] == 4 and len({*window}) == 5:
            high = window[0]
            return 5 if window == [5, 4, 3, 2, 1] else high
    return None


def _straight_sequence(high: int) -> Tuple[int, int, int, int, int]:
    if high == 5:
        return (5, 4, 3, 2, 1)
    return (high, high - 1, high - 2, high - 3, high - 4)


def _encode_tiebreak(values: Tuple[int, ...]) -> int:
    encoded = 0
    for value in values:
        encoded = (encoded << 4) | value
    return encoded


def compare_hands(hand_a: Sequence[Card], hand_b: Sequence[Card]) -> int:
    """Compare two hands given seven cards each."""

    rank_a = max((_rank_five(combo) for combo in combinations(hand_a, 5)))
    rank_b = max((_rank_five(combo) for combo in combinations(hand_b, 5)))
    return (rank_a > rank_b) - (rank_a < rank_b)


__all__ = ["rank_hand", "compare_hands", "HandRank"]
