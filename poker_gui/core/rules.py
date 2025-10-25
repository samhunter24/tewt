"""Texas Hold'em betting rules and helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class BlindStructure:
    small_blind: int
    big_blind: int
    ante: int = 0


@dataclass
class BlindLevel:
    level: int
    small_blind: int
    big_blind: int
    ante: int
    duration_minutes: int


def min_raise(current_bet: int, last_raise: int, player_stack: int) -> int:
    """Return the minimum legal raise amount."""

    min_total = current_bet + max(last_raise, current_bet)
    return min(min_total, player_stack)


def legal_bet_sizes(current_bet: int, last_raise: int, player_stack: int, pot_size: int) -> List[int]:
    """Suggest a set of canonical bet sizes (in chips)."""

    sizes = []
    min_total = current_bet if current_bet > 0 else max(last_raise, pot_size // 3 or 1)
    for multiplier in (1 / 3, 0.5, 0.75, 1.0, 1.5):
        size = int(round(pot_size * multiplier))
        if size < min_total:
            continue
        if size > player_stack:
            size = player_stack
        if size not in sizes:
            sizes.append(size)
    if player_stack not in sizes:
        sizes.append(player_stack)
    return sorted(sizes)


def rotate_button(num_players: int, current_dealer: int) -> int:
    return (current_dealer + 1) % num_players


def posting_order(num_players: int, dealer_index: int) -> Iterable[int]:
    for offset in range(1, num_players + 1):
        yield (dealer_index + offset) % num_players


__all__ = [
    "BlindStructure",
    "BlindLevel",
    "min_raise",
    "legal_bet_sizes",
    "rotate_button",
    "posting_order",
]
