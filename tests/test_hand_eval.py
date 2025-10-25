from poker_gui.core.cards import Card
from poker_gui.core.hand_eval import compare_hands, rank_hand


def make_cards(codes):
    mapping = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
    result = []
    for code in codes:
        rank = code[0]
        suit = mapping[code[1]]
        if rank == "T":
            value = 10
        elif rank == "J":
            value = 11
        elif rank == "Q":
            value = 12
        elif rank == "K":
            value = 13
        elif rank == "A":
            value = 14
        else:
            value = int(rank)
        result.append(Card(value, suit))
    return result


def test_rank_straight_flush():
    cards = make_cards(["Ah", "Kh", "Qh", "Jh", "Th", "9d", "2c"])
    category, _, description = rank_hand(cards)
    assert category == 8
    assert "Straight Flush" in description


def test_compare_pairs_vs_trips():
    hero = make_cards(["Ah", "Ad", "7s", "7h", "2d", "3c", "4s"])
    villain = make_cards(["Kh", "Kd", "Ks", "9h", "4d", "3s", "2h"])
    assert compare_hands(hero, villain) < 0


def test_rank_full_house_breaker():
    cards = make_cards(["Ah", "Ad", "Ac", "Kh", "Kd", "2s", "3d"])
    category, _, description = rank_hand(cards)
    assert category == 6
    assert "Full House" in description
