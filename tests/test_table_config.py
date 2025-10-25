import json

from poker_gui.core.table_manager import TableManager, load_table_config


def test_load_table_config_with_custom_players(tmp_path):
    config_path = tmp_path / "table.json"
    config_path.write_text(
        json.dumps(
            {
                "table_name": "Custom Table",
                "seats": 3,
                "starting_stack": 500,
                "blinds": {"small": 5, "big": 10, "ante": 1},
                "players": [
                    {"type": "human", "name": "Hero"},
                    {"type": "ai", "name": "Villain", "profile": "Solid"},
                ],
            }
        )
    )

    config = load_table_config(config_path)
    assert config.name == "Custom Table"
    assert config.seats == 3
    assert config.blinds.small_blind == 5
    assert config.blinds.big_blind == 10
    assert config.blinds.ante == 1

    manager = TableManager(config)
    assert manager.state.players[0].name == "Hero"
    assert manager.state.players[1].name == "Villain"
    # Third seat should be auto-filled as an AI player.
    assert manager.state.players[2].name.startswith("Bot ")
