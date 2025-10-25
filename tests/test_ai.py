from poker_gui.core.ai import DecisionEngine
from poker_gui.core.cards import Card
from poker_gui.core.players import AIPlayer
from poker_gui.core.table_manager import TableConfig, TableManager


def test_ai_decision_returns_legal_action():
    engine = DecisionEngine()
    player = AIPlayer(seat=0, name="Bot", stack=200)
    hole = (Card(14, "♠"), Card(13, "♠"))
    legal = [("fold", 0, 0), ("call", 20, 20), ("raise", 40, 120)]
    decision = engine.choose_preflop(player, "BTN", hole, legal)
    assert decision.move in {"fold", "call", "raise", "check"}
    if decision.amount is not None:
        min_amount = next((min_amt for move, min_amt, _ in legal if move == decision.move), 0)
        max_amount = next((max_amt for move, _, max_amt in legal if move == decision.move), min_amount)
        assert min_amount <= decision.amount <= max_amount


def test_table_manager_autoplay():
    manager = TableManager(TableConfig())
    manager.start_hand()
    for _ in range(3):
        manager.play_ai_turn(1)
    assert manager.state.players[1].stack >= 0
