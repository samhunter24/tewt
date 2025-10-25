from poker_gui.core.rules import BlindStructure, min_raise, posting_order, rotate_button


def test_min_raise_all_in_capped():
    assert min_raise(20, 20, 30) == 30


def test_posting_order_rotation():
    order = list(posting_order(6, 2))
    assert order[0] == 3
    assert order[-1] == 2


def test_rotate_button_wrap():
    assert rotate_button(6, 5) == 0
