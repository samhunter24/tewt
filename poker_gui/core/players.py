from __future__ import annotations

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .cards import Card


@dataclass
class PlayerStats:
    vpip: int = 0
    pfr: int = 0
    three_bet: int = 0
    fold_to_cbet: int = 0
    wsd: int = 0
    aggression: int = 0
    hands_played: int = 0


@dataclass
class BasePlayer:
    seat: int
    name: str
    stack: int
    is_human: bool = False
    stats: PlayerStats = field(default_factory=PlayerStats)
    profile: Optional[str] = None
    sitting_out: bool = False
    hole_cards: tuple["Card", ...] = field(default_factory=tuple)

    def bet(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("bet amount must be positive")
        if amount > self.stack:
            raise ValueError("Insufficient stack")
        self.stack -= amount

    def add_winnings(self, amount: int) -> None:
        self.stack += amount


class HumanPlayer(BasePlayer):
    is_human = True


class AIPlayer(BasePlayer):
    def __init__(self, *args, strategy: Optional[str] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.profile = strategy or self.profile or "Casual"
        self.memory: Dict[str, float] = {}


__all__ = ["BasePlayer", "HumanPlayer", "AIPlayer", "PlayerStats"]
