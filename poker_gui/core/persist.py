"""Simple JSON persistence helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parent.parent / "data"


def load_json(filename: str, default: Any) -> Any:
    path = DATA_PATH / filename
    if not path.exists():
        return default
    return json.loads(path.read_text())


def save_json(filename: str, payload: Any) -> None:
    path = DATA_PATH / filename
    path.write_text(json.dumps(payload, indent=2))


__all__ = ["load_json", "save_json"]
