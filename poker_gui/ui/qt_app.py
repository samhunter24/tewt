"""PyQt6 application bootstrap."""
from __future__ import annotations

from typing import Sequence

from PyQt6 import QtWidgets

from ..core.table_manager import TableManager
from .table import TableWindow


def launch_qt(manager: TableManager, argv: Sequence[str]) -> int:
    app = QtWidgets.QApplication(list(argv))
    window = TableWindow(manager)
    window.show()
    return app.exec()


__all__ = ["launch_qt"]
