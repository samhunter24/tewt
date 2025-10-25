"""Card and deck utilities."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List, Sequence

SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")
RANK_TO_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}
VALUE_TO_RANK = {v: r for r, v in RANK_TO_VALUE.items()}


@dataclass(frozen=True)
class Card:
    """Representation of a standard playing card."""

    rank: int
    suit: str

    def __str__(self) -> str:
        return f"{VALUE_TO_RANK[self.rank]}{self.suit}"

    def __lt__(self, other: "Card") -> bool:
        return self.rank < other.rank


class Deck:
    """A shuffled deck of cards."""

    def __init__(self, *, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._cards: List[Card] = []
        self.reset()

    def reset(self) -> None:
        self._cards = [Card(RANK_TO_VALUE[r], s) for s in SUITS for r in RANKS]
        self.shuffle()

    def shuffle(self) -> None:
        self._rng.shuffle(self._cards)

    def deal(self, count: int = 1) -> List[Card]:
        if count < 0:
            raise ValueError("count must be positive")
        if count > len(self._cards):
            raise ValueError("Not enough cards remaining")
        dealt, self._cards = self._cards[:count], self._cards[count:]
        return dealt

    def burn(self) -> None:
        if self._cards:
            self._cards.pop(0)

    def __len__(self) -> int:
        return len(self._cards)

    def remaining(self) -> Sequence[Card]:
        return tuple(self._cards)

    def remove_cards(self, cards: Iterable[Card]) -> None:
        lookup = {(card.rank, card.suit) for card in cards}
        self._cards = [card for card in self._cards if (card.rank, card.suit) not in lookup]


def parse_cards(repr_cards: Iterable[str]) -> List[Card]:
    """Parse string representations into :class:`Card` objects."""

    cards = []
    for token in repr_cards:
        rank_symbol, suit = token[0], token[1]
        cards.append(Card(RANK_TO_VALUE[rank_symbol.upper()], suit))
    return cards


__all__ = ["Card", "Deck", "parse_cards", "SUITS", "RANKS"]
