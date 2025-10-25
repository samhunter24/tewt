# Hold'em Poker GUI

This package provides a lightweight Texas Hold'em experience with a PyQt6
front-end and a clean separation between the user interface and the core game
logic. The focus is on demonstrating a professional table presentation, smart
computer opponents, and reusable logic modules that can be embedded in other
front ends.

## Features

- Cash-game style blinds with optional antes.
- Configurable table managed by `TableManager` with automated AI actions.
- Side-pot accounting and a seven-card hand evaluator with comprehensive unit tests.
- PyQt6 interface with a spectator-oriented auto-play mode and a Tkinter
  fallback for environments without Qt.
- JSON-backed persistence for table presets, themes, and bot profiles.

## Running the app

```bash
python -m poker_gui
```

If PyQt6 is available, the main table window will appear. Click **Auto Play**
to simulate a full hand against the built-in bots. When PyQt6 is missing, a
simple Tkinter window is shown with a button to run automated hands.

## Development

Install the package in editable mode with the provided `pyproject.toml` and run
pytest to execute the included unit tests.

```bash
pip install -e .
pytest
```

## License

MIT
