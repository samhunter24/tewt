"""Pot accounting for Hold'em tables."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence


@dataclass
class SidePot:
    amount: int
    eligible_seats: List[int]


@dataclass
class SidePotManager:
    """Tracks contributions and builds side pots."""

    contributions: Dict[int, int] = field(default_factory=dict)

    def add_bet(self, seat: int, amount: int) -> None:
        self.contributions[seat] = self.contributions.get(seat, 0) + amount

    def build(self, active_seats: Sequence[int]) -> List[SidePot]:
        """Construct side pots from the contributions."""

        remaining = dict(self.contributions)
        pots: List[SidePot] = []
        while remaining:
            eligible = [seat for seat in active_seats if seat in remaining]
            if not eligible:
                break
            min_contribution = min(remaining[seat] for seat in eligible)
            amount = min_contribution * len([seat for seat in remaining if remaining[seat] > 0])
            pots.append(SidePot(amount=amount, eligible_seats=list(eligible)))
            for seat in list(remaining):
                remaining[seat] -= min_contribution
                if remaining[seat] <= 0:
                    del remaining[seat]
        return pots

    def reset(self) -> None:
        self.contributions.clear()


__all__ = ["SidePot", "SidePotManager"]
