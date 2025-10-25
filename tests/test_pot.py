from poker_gui.core.pot import SidePotManager


def test_side_pot_multiple_all_in():
    manager = SidePotManager()
    manager.add_bet(0, 50)
    manager.add_bet(1, 100)
    manager.add_bet(2, 200)
    pots = manager.build([0, 1, 2])
    assert len(pots) == 3
    amounts = [pot.amount for pot in pots]
    assert amounts == [150, 100, 100]
    assert pots[0].eligible_seats == [0, 1, 2]
    assert pots[-1].eligible_seats == [2]
