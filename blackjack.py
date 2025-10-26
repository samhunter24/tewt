"""Blackjack (21) game with Tkinter GUI."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import tkinter as tk
from tkinter import messagebox

# ----------------------- Configuration ------------------------------------

APP_TITLE = "Blackjack"
SAVE_FILE = Path("blackjack_save.json")
STARTING_BANKROLL = 1000.0
MIN_BET = 5.0
DEALER_HITS_SOFT_17 = True
ANIMATION_DELAY = 250  # milliseconds between animated actions
CARD_WIDTH = 70
CARD_HEIGHT = 100
CARD_SPACING = 20
HAND_SPACING = 160
TABLE_PADDING = 40

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
CARD_VALUES: Dict[str, int] = {
    "A": 11,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 10,
    "Q": 10,
    "K": 10,
}


# ----------------------- Core game models ---------------------------------


def card_value(rank: str) -> int:
    """Return nominal value for a card rank."""
    return CARD_VALUES[rank]


@dataclass
class Card:
    """Representation of a single playing card."""

    rank: str
    suit: str

    @property
    def value(self) -> int:
        return card_value(self.rank)

    @property
    def display(self) -> str:
        return f"{self.rank}{self.suit}"


class Deck:
    """A single 52-card deck."""

    def __init__(self, cards: Optional[List[Card]] = None) -> None:
        if cards is not None:
            self.cards: List[Card] = cards
        else:
            self.cards = []
            self.reset()

    def reset(self) -> None:
        """Create a new shuffled deck."""
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        random.shuffle(self.cards)

    def draw(self) -> Card:
        if not self.cards:
            self.reset()
        return self.cards.pop()

    def cards_remaining(self) -> int:
        return len(self.cards)

    def needs_reshuffle(self) -> bool:
        return len(self.cards) < 15

    def to_json(self) -> List[Tuple[str, str]]:
        return [(card.rank, card.suit) for card in self.cards]

    @classmethod
    def from_json(cls, data: Sequence[Sequence[str]]) -> "Deck":
        cards = [Card(rank, suit) for rank, suit in data]
        return cls(cards)


@dataclass
class Hand:
    """A hand of cards."""

    cards: List[Card] = field(default_factory=list)

    def add_card(self, card: Card) -> None:
        self.cards.append(card)

    def best_value(self) -> int:
        total = sum(card.value for card in self.cards)
        aces = sum(1 for card in self.cards if card.rank == "A")
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def is_soft(self) -> bool:
        total = sum(card.value for card in self.cards)
        aces = sum(1 for card in self.cards if card.rank == "A")
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return aces > 0 and total <= 21

    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.best_value() == 21

    def is_bust(self) -> bool:
        return self.best_value() > 21

    def clear(self) -> None:
        self.cards.clear()


@dataclass
class PlayerHand:
    """Player hand with bet metadata."""

    hand: Hand
    bet: float
    is_doubled: bool = False
    is_finished: bool = False
    surrendered: bool = False
    is_split_hand: bool = False

    def can_double(self) -> bool:
        return len(self.hand.cards) == 2 and not self.is_doubled and not self.surrendered

    def can_split(self) -> bool:
        if len(self.hand.cards) != 2:
            return False
        return self.hand.cards[0].rank == self.hand.cards[1].rank


class GameState:
    """Encapsulates the non-UI Blackjack logic and persistence."""

    def __init__(self, bankroll: float, deck: Deck, stats: Dict[str, float]) -> None:
        self.bankroll: float = bankroll
        self.deck = deck
        self.stats = stats
        self.phase: str = "betting"
        self.current_bet: float = 0.0
        self.player_hands: List[PlayerHand] = []
        self.current_hand_index: int = 0
        self.dealer_hand: Hand = Hand()
        self.hide_dealer_hole: bool = True
        self.round_messages: List[str] = []
        self.insurance_bet: float = 0.0
        self.insurance_taken: bool = False
        self.has_split_this_round: bool = False

    # ---------------- Persistence ----------------

    @classmethod
    def load(cls) -> "GameState":
        if SAVE_FILE.exists():
            try:
                with SAVE_FILE.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                bankroll = float(data.get("bankroll", STARTING_BANKROLL))
                deck_data = data.get("deck")
                if deck_data:
                    deck = Deck.from_json(deck_data)
                else:
                    deck = Deck()
                stats = data.get("stats", {})
            except (OSError, ValueError, KeyError):
                bankroll = STARTING_BANKROLL
                deck = Deck()
                stats = {}
        else:
            bankroll = STARTING_BANKROLL
            deck = Deck()
            stats = {}

        stats.setdefault("wins", 0)
        stats.setdefault("losses", 0)
        stats.setdefault("pushes", 0)
        stats.setdefault("rounds", 0)
        stats.setdefault("net_profit", 0.0)
        stats.setdefault("best_streak", 0)
        stats.setdefault("current_streak", 0)
        return cls(bankroll=bankroll, deck=deck, stats=stats)

    def save(self) -> None:
        data = {
            "bankroll": self.bankroll,
            "deck": self.deck.to_json(),
            "stats": self.stats,
        }
        try:
            with SAVE_FILE.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except OSError:
            pass

    # ---------------- Round management ----------------

    def start_round(self, bet: float) -> None:
        if self.phase not in {"betting", "round_over"}:
            raise RuntimeError("Cannot start round right now")
        if bet < MIN_BET:
            raise ValueError(f"Minimum bet is ${MIN_BET:.0f}")
        if bet > self.bankroll:
            raise ValueError("Insufficient bankroll for that bet")

        if self.deck.needs_reshuffle():
            self.deck.reset()

        self.phase = "dealing"
        self.current_bet = bet
        self.bankroll -= bet
        self.player_hands = [PlayerHand(hand=Hand(), bet=bet)]
        self.current_hand_index = 0
        self.dealer_hand = Hand()
        self.hide_dealer_hole = True
        self.round_messages = []
        self.insurance_bet = 0.0
        self.insurance_taken = False
        self.has_split_this_round = False
        self.save()

    def current_hand(self) -> Optional[PlayerHand]:
        if not self.player_hands:
            return None
        if 0 <= self.current_hand_index < len(self.player_hands):
            return self.player_hands[self.current_hand_index]
        return None

    def deal_card_to_player(self, hand_index: Optional[int] = None) -> Card:
        if hand_index is None:
            hand_index = self.current_hand_index
        card = self.deck.draw()
        self.player_hands[hand_index].hand.add_card(card)
        self.save()
        return card

    def deal_card_to_dealer(self) -> Card:
        card = self.deck.draw()
        self.dealer_hand.add_card(card)
        self.save()
        return card

    def reveal_dealer_hole(self) -> None:
        self.hide_dealer_hole = False

    def dealer_upcard(self) -> Optional[Card]:
        if not self.dealer_hand.cards:
            return None
        if self.hide_dealer_hole:
            if len(self.dealer_hand.cards) >= 2:
                return self.dealer_hand.cards[1]
            return None
        return self.dealer_hand.cards[0]

    def can_offer_insurance(self) -> bool:
        if not self.dealer_hand.cards:
            return False
        upcard = self.dealer_upcard()
        return (
            self.phase in {"player", "dealing"}
            and upcard is not None
            and upcard.rank == "A"
            and not self.insurance_taken
            and self.bankroll >= self.current_bet / 2
        )

    def buy_insurance(self) -> float:
        max_insurance = min(self.current_bet / 2, self.bankroll)
        self.insurance_bet = max_insurance
        self.bankroll -= max_insurance
        self.insurance_taken = True
        self.save()
        return max_insurance

    def can_double(self) -> bool:
        hand = self.current_hand()
        if not hand or self.phase != "player":
            return False
        if not hand.can_double():
            return False
        return self.bankroll >= hand.bet

    def can_split(self) -> bool:
        if self.phase != "player" or self.has_split_this_round:
            return False
        hand = self.current_hand()
        if not hand or not hand.can_split():
            return False
        return self.bankroll >= hand.bet

    def can_surrender(self) -> bool:
        hand = self.current_hand()
        return (
            self.phase == "player"
            and hand is not None
            and not hand.surrendered
            and len(hand.hand.cards) == 2
        )

    def split_current_hand(self) -> Tuple[int, int]:
        hand = self.current_hand()
        if not hand:
            raise RuntimeError("No hand to split")
        if not self.can_split():
            raise RuntimeError("Cannot split right now")

        self.bankroll -= hand.bet
        card_two = hand.hand.cards.pop()
        new_hand = PlayerHand(hand=Hand([card_two]), bet=hand.bet, is_split_hand=True)
        hand.is_split_hand = True
        self.player_hands.insert(self.current_hand_index + 1, new_hand)
        self.has_split_this_round = True
        self.save()
        return self.current_hand_index, self.current_hand_index + 1

    def double_current_hand(self) -> None:
        hand = self.current_hand()
        if not hand or not self.can_double():
            raise RuntimeError("Cannot double")
        self.bankroll -= hand.bet
        hand.bet *= 2
        hand.is_doubled = True
        self.save()

    def surrender_current_hand(self) -> None:
        hand = self.current_hand()
        if not hand or not self.can_surrender():
            raise RuntimeError("Cannot surrender")
        refund = hand.bet / 2
        self.bankroll += refund
        hand.surrendered = True
        hand.is_finished = True
        self.round_messages.append(
            f"Hand {self.current_hand_index + 1} surrendered. Refund ${refund:.2f}."
        )
        self.save()

    def advance_to_next_hand(self) -> bool:
        while self.current_hand_index < len(self.player_hands):
            hand = self.player_hands[self.current_hand_index]
            if not hand.is_finished and not hand.hand.is_bust() and not hand.surrendered:
                return True
            self.current_hand_index += 1
        self.phase = "dealer"
        return False

    def any_active_hand(self) -> bool:
        return any(
            not h.hand.is_bust() and not h.surrendered for h in self.player_hands
        )

    def dealer_should_draw(self) -> bool:
        if not self.any_active_hand():
            return False
        value = self.dealer_hand.best_value()
        soft = self.dealer_hand.is_soft()
        if value < 17:
            return True
        if value == 17 and soft and DEALER_HITS_SOFT_17:
            return True
        return False

    def resolve_round(self) -> Dict[str, object]:
        dealer_value = self.dealer_hand.best_value()
        dealer_blackjack = self.dealer_hand.is_blackjack()
        dealer_bust = dealer_value > 21

        summary: List[str] = []
        round_profit = 0.0

        if self.insurance_taken:
            if dealer_blackjack:
                insurance_win = self.insurance_bet * 3
                self.bankroll += insurance_win
                round_profit += insurance_win - self.insurance_bet
                summary.append(
                    f"Insurance won ${insurance_win - self.insurance_bet:.2f}."
                )
            else:
                summary.append(f"Insurance lost ${self.insurance_bet:.2f}.")
                round_profit -= self.insurance_bet

        for idx, p_hand in enumerate(self.player_hands, start=1):
            result: str
            if p_hand.surrendered:
                result = f"Hand {idx}: Surrendered."
                round_profit -= p_hand.bet / 2
                self.stats["losses"] += 1
            elif p_hand.hand.is_bust():
                result = f"Hand {idx}: Busted."
                round_profit -= p_hand.bet
                self.stats["losses"] += 1
            else:
                player_value = p_hand.hand.best_value()
                player_blackjack = p_hand.hand.is_blackjack() and not p_hand.is_split_hand
                payout = 0.0
                if dealer_blackjack and not player_blackjack:
                    result = f"Hand {idx}: Dealer blackjack."
                    round_profit -= p_hand.bet
                    self.stats["losses"] += 1
                elif player_blackjack and not dealer_blackjack:
                    payout = p_hand.bet * 2.5
                    self.bankroll += payout
                    result = f"Hand {idx}: Blackjack! Won ${payout - p_hand.bet:.2f}."
                    round_profit += payout - p_hand.bet
                    self.stats["wins"] += 1
                elif dealer_bust:
                    payout = p_hand.bet * 2
                    self.bankroll += payout
                    result = f"Hand {idx}: Dealer busts, win ${payout - p_hand.bet:.2f}."
                    round_profit += payout - p_hand.bet
                    self.stats["wins"] += 1
                else:
                    if player_value > dealer_value:
                        payout = p_hand.bet * 2
                        self.bankroll += payout
                        result = f"Hand {idx}: Win ${payout - p_hand.bet:.2f}."
                        round_profit += payout - p_hand.bet
                        self.stats["wins"] += 1
                    elif player_value == dealer_value:
                        payout = p_hand.bet
                        self.bankroll += payout
                        result = f"Hand {idx}: Push."
                        self.stats["pushes"] += 1
                    else:
                        result = f"Hand {idx}: Lose."
                        round_profit -= p_hand.bet
                        self.stats["losses"] += 1
            summary.append(result)

        self.stats["rounds"] += 1
        self.stats["net_profit"] += round_profit
        if round_profit > 0:
            current = self.stats.get("current_streak", 0)
            current = current + 1 if current > 0 else 1
            self.stats["current_streak"] = current
            self.stats["best_streak"] = max(self.stats.get("best_streak", 0), current)
        elif round_profit < 0:
            current = self.stats.get("current_streak", 0)
            current = current - 1 if current < 0 else -1
            self.stats["current_streak"] = current
        else:
            self.stats["current_streak"] = 0

        self.phase = "round_over"
        self.current_bet = 0.0
        self.insurance_bet = 0.0
        self.insurance_taken = False
        self.save()
        return {
            "dealer_value": dealer_value,
            "dealer_bust": dealer_bust,
            "dealer_blackjack": dealer_blackjack,
            "messages": summary,
            "round_profit": round_profit,
        }


# ----------------------- Strategy helper ----------------------------------


def basic_strategy_hint(hand: Hand, dealer_card: Optional[Card], can_split: bool) -> str:
    if dealer_card is None:
        return ""
    if hand.is_blackjack():
        return "Stand"
    if can_split and len(hand.cards) == 2:
        rank = hand.cards[0].rank
        dealer_val = dealer_card.value
        split_advices = {
            "A": "Split",
            "8": "Split",
            "9": "Split" if dealer_val in {2, 3, 4, 5, 6, 8, 9} else "Stand",
            "7": "Split" if dealer_val in {2, 3, 4, 5, 6, 7} else "Hit",
            "6": "Split" if dealer_val in {2, 3, 4, 5, 6} else "Hit",
            "5": "Double" if dealer_val in {2, 3, 4, 5, 6, 7, 8, 9} else "Hit",
            "4": "Split" if dealer_val in {5, 6} else "Hit",
            "3": "Split" if dealer_val in {4, 5, 6, 7} else "Hit",
            "2": "Split" if dealer_val in {4, 5, 6, 7} else "Hit",
            "10": "Stand",
        }
        if rank in split_advices:
            return split_advices[rank]

    total = hand.best_value()
    dealer_val = dealer_card.value
    if hand.is_soft() and any(card.rank == "A" for card in hand.cards):
        if total <= 17:
            return "Hit"
        if total == 18:
            if dealer_val in {2, 7, 8}:
                return "Stand"
            if dealer_val in {3, 4, 5, 6}:
                return "Double"
            return "Hit"
        return "Stand"

    if total <= 8:
        return "Hit"
    if total == 9:
        return "Double" if dealer_val in {3, 4, 5, 6} else "Hit"
    if total == 10:
        return "Double" if dealer_val in {2, 3, 4, 5, 6, 7, 8, 9} else "Hit"
    if total == 11:
        return "Double" if dealer_val != 11 else "Hit"
    if total == 12:
        return "Stand" if dealer_val in {4, 5, 6} else "Hit"
    if 13 <= total <= 16:
        return "Stand" if dealer_val in {2, 3, 4, 5, 6} else "Hit"
    return "Stand"


# ----------------------- GUI application ----------------------------------


class BlackjackApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.resizable(False, False)
        self.configure(bg="#063b1a")

        self.state_logic = GameState.load()

        self.message_var = tk.StringVar(value="Place your bet to begin.")
        self.bankroll_var = tk.StringVar()
        self.bet_var = tk.StringVar(value=f"{MIN_BET:.0f}")
        self.hint_var = tk.StringVar(value="")

        self.summary_overlay_text = ""
        self.waiting_on_initial = False

        self._build_layout()
        self._bind_shortcuts()
        self.after(100, self._refresh_ui)

    def _build_layout(self) -> None:
        self.table_canvas = tk.Canvas(
            self,
            width=800,
            height=520,
            bg="#0f5e2d",
            highlightthickness=0,
        )
        self.table_canvas.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

        controls = tk.Frame(self, bg="#063b1a")
        controls.grid(row=1, column=0, sticky="w", padx=10)

        self.hit_button = tk.Button(controls, text="Hit (H)", width=10, command=self.on_hit)
        self.stand_button = tk.Button(controls, text="Stand (S)", width=10, command=self.on_stand)
        self.double_button = tk.Button(controls, text="Double (D)", width=10, command=self.on_double)
        self.split_button = tk.Button(controls, text="Split (P)", width=10, command=self.on_split)
        self.surrender_button = tk.Button(controls, text="Surrender", width=10, command=self.on_surrender)
        self.insurance_button = tk.Button(controls, text="Insurance", width=10, command=self.on_insurance)

        self.hit_button.grid(row=0, column=0, padx=4, pady=4)
        self.stand_button.grid(row=0, column=1, padx=4, pady=4)
        self.double_button.grid(row=0, column=2, padx=4, pady=4)
        self.split_button.grid(row=0, column=3, padx=4, pady=4)
        self.surrender_button.grid(row=0, column=4, padx=4, pady=4)
        self.insurance_button.grid(row=0, column=5, padx=4, pady=4)

        bet_panel = tk.Frame(self, bg="#063b1a")
        bet_panel.grid(row=1, column=1, sticky="ew")

        tk.Label(bet_panel, text="Bet:", fg="white", bg="#063b1a").grid(row=0, column=0, padx=4)
        self.bet_entry = tk.Entry(bet_panel, textvariable=self.bet_var, width=10, justify="right")
        self.bet_entry.grid(row=0, column=1, padx=4)

        self.chip_buttons: List[tk.Button] = []
        for idx, val in enumerate((5, 25, 100), start=2):
            btn = tk.Button(
                bet_panel,
                text=f"+${val}",
                width=6,
                command=lambda v=val: self.on_chip(v),
            )
            btn.grid(row=0, column=idx, padx=2)
            self.chip_buttons.append(btn)

        self.deal_button = tk.Button(bet_panel, text="Deal (N)", width=12, command=self.on_deal)
        self.deal_button.grid(row=0, column=5, padx=6)

        right_panel = tk.Frame(self, bg="#063b1a")
        right_panel.grid(row=1, column=2, sticky="e", padx=10)

        self.stats_button = tk.Button(right_panel, text="Stats", command=self.show_stats)
        self.stats_button.grid(row=0, column=0, padx=4)

        self.hint_label = tk.Label(right_panel, textvariable=self.hint_var, fg="white", bg="#063b1a")
        self.hint_label.grid(row=0, column=1, padx=4)

        message_frame = tk.Frame(self, bg="#063b1a")
        message_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))

        self.message_label = tk.Label(
            message_frame,
            textvariable=self.message_var,
            fg="white",
            bg="#063b1a",
            font=("Helvetica", 12),
        )
        self.message_label.pack(side="left")

        self.status_label = tk.Label(
            message_frame,
            textvariable=self.bankroll_var,
            fg="white",
            bg="#063b1a",
            font=("Helvetica", 12, "bold"),
        )
        self.status_label.pack(side="right")

    def _bind_shortcuts(self) -> None:
        self.bind("<KeyPress-h>", lambda _event: self.on_hit())
        self.bind("<KeyPress-H>", lambda _event: self.on_hit())
        self.bind("<KeyPress-s>", lambda _event: self.on_stand())
        self.bind("<KeyPress-S>", lambda _event: self.on_stand())
        self.bind("<KeyPress-d>", lambda _event: self.on_double())
        self.bind("<KeyPress-D>", lambda _event: self.on_double())
        self.bind("<KeyPress-p>", lambda _event: self.on_split())
        self.bind("<KeyPress-P>", lambda _event: self.on_split())
        self.bind("<KeyPress-n>", lambda _event: self.on_deal())
        self.bind("<KeyPress-N>", lambda _event: self.on_deal())

    def _refresh_ui(self) -> None:
        self._update_status_text()
        self._update_controls()
        self._draw_table()
        self._update_hint()
        self.after(200, self._refresh_ui)

    def _update_status_text(self) -> None:
        deck_remaining = self.state_logic.deck.cards_remaining()
        text = (
            f"Bankroll: ${self.state_logic.bankroll:,.2f}    "
            f"Deck Remaining: {deck_remaining}"
        )
        if self.state_logic.phase in {"player", "dealing"}:
            active = sum(hand.bet for hand in self.state_logic.player_hands)
            text += f"    Active Wager: ${active:,.2f}"
        self.bankroll_var.set(text)

    def _update_controls(self) -> None:
        phase = self.state_logic.phase
        betting_phase = phase in {"betting", "round_over"}

        def enable(widget: tk.Widget, value: bool) -> None:
            widget.configure(state=tk.NORMAL if value else tk.DISABLED)

        enable(self.deal_button, betting_phase or phase == "betting")
        enable(self.bet_entry, betting_phase)
        for btn in self.chip_buttons:
            enable(btn, betting_phase)

        can_hit = phase == "player"
        enable(self.hit_button, can_hit)
        enable(self.stand_button, can_hit)
        enable(self.double_button, self.state_logic.can_double())
        enable(self.split_button, self.state_logic.can_split())
        enable(self.surrender_button, self.state_logic.can_surrender())
        enable(self.insurance_button, self.state_logic.can_offer_insurance())

        if phase == "round_over":
            self.deal_button.configure(text="Next Round (N)")
        else:
            self.deal_button.configure(text="Deal (N)")

    def _update_hint(self) -> None:
        if self.state_logic.phase != "player":
            self.hint_var.set("")
            return
        hand = self.state_logic.current_hand()
        dealer_upcard = self.state_logic.dealer_upcard()
        if hand is None or dealer_upcard is None:
            self.hint_var.set("")
            return
        hint = basic_strategy_hint(hand.hand, dealer_upcard, self.state_logic.can_split())
        self.hint_var.set(f"Hint: {hint}")

    def _draw_card(self, x: int, y: int, card: Optional[Card], face_down: bool = False) -> None:
        if not face_down and card:
            is_red = card.suit in {"♥", "♦"}
            text_color = "#e63946" if is_red else "white"
            self.table_canvas.create_rectangle(
                x,
                y,
                x + CARD_WIDTH,
                y + CARD_HEIGHT,
                outline="white",
                width=2,
                fill="#0d3e1e",
            )
            self.table_canvas.create_text(
                x + CARD_WIDTH / 2,
                y + CARD_HEIGHT / 2,
                text=card.display,
                font=("Helvetica", 16, "bold"),
                fill=text_color,
            )
        else:
            self.table_canvas.create_rectangle(
                x,
                y,
                x + CARD_WIDTH,
                y + CARD_HEIGHT,
                outline="white",
                width=2,
                fill="#1c2c4c",
            )
            self.table_canvas.create_text(
                x + CARD_WIDTH / 2,
                y + CARD_HEIGHT / 2,
                text="♠♦",
                font=("Helvetica", 18, "bold"),
                fill="gold",
            )

    def _draw_table(self) -> None:
        self.table_canvas.delete("all")
        self.table_canvas.create_rectangle(0, 0, 800, 520, fill="#0f5e2d", outline="")

        self.table_canvas.create_text(
            400,
            40,
            text="Dealer",
            font=("Helvetica", 18, "bold"),
            fill="white",
        )
        dealer_y = 70
        x = (800 - CARD_WIDTH * max(2, len(self.state_logic.dealer_hand.cards))) / 2
        for idx, card in enumerate(self.state_logic.dealer_hand.cards):
            face_down = idx == 0 and self.state_logic.hide_dealer_hole
            self._draw_card(int(x + idx * (CARD_WIDTH + CARD_SPACING)), dealer_y, card, face_down)

        if not self.state_logic.hide_dealer_hole:
            dealer_total = self.state_logic.dealer_hand.best_value()
            self.table_canvas.create_text(
                400,
                dealer_y + CARD_HEIGHT + 30,
                text=f"Dealer: {dealer_total}",
                font=("Helvetica", 14, "bold"),
                fill="white",
            )

        self.table_canvas.create_text(
            400,
            260,
            text="Player",
            font=("Helvetica", 18, "bold"),
            fill="white",
        )

        base_y = 300
        for idx, player_hand in enumerate(self.state_logic.player_hands):
            hand_x = TABLE_PADDING + idx * HAND_SPACING
            if len(self.state_logic.player_hands) == 1:
                hand_x = (800 - CARD_WIDTH * max(2, len(player_hand.hand.cards))) / 2
            for card_idx, card in enumerate(player_hand.hand.cards):
                self._draw_card(
                    int(hand_x + card_idx * (CARD_WIDTH + CARD_SPACING)),
                    base_y,
                    card,
                )
            label = f"Hand {idx + 1}: ${player_hand.bet:.2f}"
            if player_hand.is_doubled:
                label += " (Doubled)"
            if player_hand.surrendered:
                label += " (Surrendered)"
            if player_hand.hand.is_bust():
                label += " (Bust)"
            y_offset = base_y + CARD_HEIGHT + 25
            self.table_canvas.create_text(
                int(hand_x + CARD_WIDTH),
                y_offset,
                text=label,
                font=("Helvetica", 12, "bold"),
                fill="yellow" if idx == self.state_logic.current_hand_index and self.state_logic.phase == "player" else "white",
            )

        if self.state_logic.phase == "round_over" and self.summary_overlay_text:
            self.table_canvas.create_rectangle(
                100,
                180,
                700,
                360,
                fill="#0a331b",
                outline="white",
                width=3,
            )
            self.table_canvas.create_text(
                400,
                270,
                text=self.summary_overlay_text,
                font=("Helvetica", 14),
                fill="white",
                width=560,
            )

    # ------------------- Actions -----------------------------------------

    def on_chip(self, value: int) -> None:
        try:
            current = float(self.bet_var.get())
        except ValueError:
            current = 0.0
        current += value
        self.bet_var.set(f"{current:.0f}")

    def on_deal(self) -> None:
        if self.state_logic.phase == "player":
            return
        if self.state_logic.phase == "round_over":
            self.state_logic.phase = "betting"
            self.summary_overlay_text = ""
            self.message_var.set("Place your bet.")
            self.state_logic.player_hands = []
            self.state_logic.dealer_hand = Hand()
            self.state_logic.current_hand_index = 0
            self.state_logic.hide_dealer_hole = True
            self._draw_table()
            self._update_controls()
            return
        try:
            bet = float(self.bet_var.get())
        except ValueError:
            messagebox.showerror("Invalid Bet", "Please enter a numeric bet amount.")
            return
        try:
            self.state_logic.start_round(bet)
        except ValueError as exc:
            messagebox.showerror("Bet Error", str(exc))
            return
        except RuntimeError as exc:
            messagebox.showerror("Game Error", str(exc))
            return
        self.message_var.set("Dealing...")
        self.waiting_on_initial = True
        self.after(ANIMATION_DELAY, self._initial_deal_sequence)

    def _initial_deal_sequence(self) -> None:
        order = [
            (self._deal_player_card, {}),
            (self._deal_dealer_card, {"hide": True}),
            (self._deal_player_card, {}),
            (self._deal_dealer_card, {"hide": False}),
        ]

        def run_step(index: int) -> None:
            if index >= len(order):
                self.waiting_on_initial = False
                self._after_initial_deal()
                return
            func, kwargs = order[index]
            func(**kwargs)
            self.after(ANIMATION_DELAY, lambda: run_step(index + 1))

        run_step(0)

    def _deal_player_card(self) -> None:
        card = self.state_logic.deal_card_to_player()
        self.message_var.set(f"Player receives {card.display}.")
        self._draw_table()

    def _deal_dealer_card(self, hide: bool) -> None:
        card = self.state_logic.deal_card_to_dealer()
        if hide:
            self.state_logic.hide_dealer_hole = True
            self.message_var.set("Dealer receives hole card.")
        else:
            self.message_var.set(f"Dealer shows {card.display}.")
        self._draw_table()

    def _after_initial_deal(self) -> None:
        dealer_blackjack = self.state_logic.dealer_hand.is_blackjack()
        player_hand = self.state_logic.player_hands[0]
        player_blackjack = player_hand.hand.is_blackjack()

        if dealer_blackjack:
            self.state_logic.reveal_dealer_hole()
            self._draw_table()
            self.message_var.set("Dealer has blackjack!")
            self.after(ANIMATION_DELAY, self.finish_round)
            return

        if player_blackjack:
            player_hand.is_finished = True
            self.state_logic.phase = "dealer"
            self.state_logic.reveal_dealer_hole()
            self._draw_table()
            self.after(ANIMATION_DELAY, self.finish_round)
            return

        self.state_logic.phase = "player"
        if self.state_logic.can_offer_insurance():
            self.message_var.set("Dealer shows Ace. Insurance available or play your hand.")
        else:
            self.message_var.set("Your move: Hit, Stand, Double, Split, or Surrender.")
        self._draw_table()
        self._update_controls()

    def on_hit(self) -> None:
        if self.state_logic.phase != "player":
            return
        card = self.state_logic.deal_card_to_player()
        self.message_var.set(f"You draw {card.display}.")
        self._draw_table()
        current = self.state_logic.current_hand()
        if current and current.hand.is_bust():
            current.is_finished = True
            self.message_var.set("Bust! Moving to next hand.")
            self.state_logic.current_hand_index += 1
            if not self.state_logic.advance_to_next_hand():
                self.after(ANIMATION_DELAY, self._start_dealer_turn)
            else:
                self.message_var.set(
                    f"Bust! Hand {self.state_logic.current_hand_index + 1}: choose your move."
                )
        self._update_controls()

    def on_stand(self) -> None:
        if self.state_logic.phase != "player":
            return
        hand = self.state_logic.current_hand()
        if not hand:
            return
        hand.is_finished = True
        self.message_var.set("You stand.")
        self.state_logic.current_hand_index += 1
        if not self.state_logic.advance_to_next_hand():
            self.after(ANIMATION_DELAY, self._start_dealer_turn)
        else:
            self.message_var.set(
                f"Hand {self.state_logic.current_hand_index + 1}: choose your move."
            )
        self._update_controls()

    def on_double(self) -> None:
        if self.state_logic.phase != "player":
            return
        try:
            self.state_logic.double_current_hand()
        except RuntimeError as exc:
            messagebox.showerror("Cannot Double", str(exc))
            return
        card = self.state_logic.deal_card_to_player()
        self.message_var.set(f"Double down! Draw {card.display} and stand.")
        hand = self.state_logic.current_hand()
        if hand:
            hand.is_finished = True
        self.state_logic.current_hand_index += 1
        self._draw_table()
        if not self.state_logic.advance_to_next_hand():
            self.after(ANIMATION_DELAY, self._start_dealer_turn)
        else:
            self.message_var.set(
                f"Hand {self.state_logic.current_hand_index + 1}: choose your move."
            )
        self._update_controls()

    def on_split(self) -> None:
        if self.state_logic.phase != "player":
            return
        try:
            first_idx, second_idx = self.state_logic.split_current_hand()
        except RuntimeError as exc:
            messagebox.showerror("Cannot Split", str(exc))
            return
        self.message_var.set("Hand split! Dealing to first hand.")
        self._draw_table()

        def deal_after_split(step: int = 0) -> None:
            sequence = [
                (first_idx, "First"),
                (second_idx, "Second"),
            ]
            if step >= len(sequence):
                self.state_logic.phase = "player"
                self.state_logic.current_hand_index = first_idx
                self.message_var.set("Play your first hand.")
                self._draw_table()
                self._update_controls()
                return
            idx, name = sequence[step]
            self.state_logic.current_hand_index = idx
            card = self.state_logic.deal_card_to_player(idx)
            self.message_var.set(f"{name} hand receives {card.display}.")
            self._draw_table()
            self.after(ANIMATION_DELAY, lambda: deal_after_split(step + 1))

        self.state_logic.phase = "dealing"
        deal_after_split()

    def on_surrender(self) -> None:
        if self.state_logic.phase != "player":
            return
        try:
            self.state_logic.surrender_current_hand()
        except RuntimeError as exc:
            messagebox.showerror("Cannot Surrender", str(exc))
            return
        self.state_logic.current_hand_index += 1
        if not self.state_logic.advance_to_next_hand():
            self.after(ANIMATION_DELAY, self._start_dealer_turn)
            self.message_var.set("Hand surrendered.")
        else:
            self.message_var.set(
                f"Hand surrendered. Hand {self.state_logic.current_hand_index + 1}: choose your move."
            )
        self._draw_table()
        self._update_controls()

    def on_insurance(self) -> None:
        if not self.state_logic.can_offer_insurance():
            return
        amount = self.state_logic.buy_insurance()
        self.message_var.set(f"Insurance purchased for ${amount:.2f}.")
        self._update_controls()

    def _start_dealer_turn(self) -> None:
        self.state_logic.phase = "dealer"
        self.state_logic.reveal_dealer_hole()
        self._draw_table()
        if not self.state_logic.any_active_hand():
            self.after(ANIMATION_DELAY, self.finish_round)
            return
        self.message_var.set("Dealer's turn.")
        self.after(ANIMATION_DELAY, self._dealer_draw_step)

    def _dealer_draw_step(self) -> None:
        if self.state_logic.dealer_should_draw():
            card = self.state_logic.deal_card_to_dealer()
            self.message_var.set(f"Dealer draws {card.display}.")
            self._draw_table()
            self.after(ANIMATION_DELAY, self._dealer_draw_step)
        else:
            self.after(ANIMATION_DELAY, self.finish_round)

    def finish_round(self) -> None:
        result = self.state_logic.resolve_round()
        messages = "\n".join(result["messages"])
        profit = result["round_profit"]
        dealer_info = "Dealer busts!" if result["dealer_bust"] else f"Dealer total: {result['dealer_value']}"
        profit_text = f"Net {'+' if profit >= 0 else ''}{profit:.2f}"
        summary = f"{dealer_info}\n{messages}\n{profit_text}"
        self.summary_overlay_text = summary
        self.message_var.set("Round complete. Press Deal for next round.")
        self._draw_table()

    def on_hit_key(self, _event: tk.Event) -> None:
        self.on_hit()

    def show_stats(self) -> None:
        stats = self.state_logic.stats
        top = tk.Toplevel(self)
        top.title("Blackjack Stats")
        top.configure(bg="#063b1a")
        labels = [
            f"Rounds: {stats['rounds']}",
            f"Wins: {stats['wins']}",
            f"Losses: {stats['losses']}",
            f"Pushes: {stats['pushes']}",
            f"Net Profit: ${stats['net_profit']:.2f}",
            f"Best Streak: {stats['best_streak']}",
            f"Current Streak: {stats['current_streak']}",
            f"Bankroll: ${self.state_logic.bankroll:,.2f}",
            f"Deck Remaining: {self.state_logic.deck.cards_remaining()}",
        ]
        for idx, text in enumerate(labels):
            tk.Label(top, text=text, fg="white", bg="#063b1a", font=("Helvetica", 12)).grid(
                row=idx, column=0, padx=10, pady=4, sticky="w"
            )
        tk.Button(top, text="Close", command=top.destroy).grid(row=len(labels), column=0, pady=10)


def main() -> None:
    app = BlackjackApp()
    app.mainloop()


if __name__ == "__main__":
    main()
