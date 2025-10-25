"""Application bootstrap for the poker GUI."""
from __future__ import annotations

import logging
import sys
from typing import Optional

from .core.table_manager import TableManager, create_default_table

LOGGER = logging.getLogger(__name__)


def run(argv: Optional[list[str]] = None) -> int:
    """Run the poker GUI application."""

    argv = list(sys.argv if argv is None else argv)
    try:
        from .ui.qt_app import launch_qt
    except Exception as exc:  # pragma: no cover - Qt not available during tests
        LOGGER.warning("Falling back to Tkinter UI due to PyQt6 load failure")
        LOGGER.debug("PyQt6 import error: %s", exc)
        from .ui.tk_app import launch_tk

        try:
            return launch_tk(create_default_table())
        except Exception as tk_exc:  # pragma: no cover - headless CI
            LOGGER.warning("Tkinter fallback unavailable")
            print("Unable to launch a graphical interface in this environment.")
            return 1

    return launch_qt(create_default_table(), argv)


__all__ = ["run", "TableManager"]
