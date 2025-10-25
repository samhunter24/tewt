"""Reusable Qt widgets for the poker UI."""
from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


class CardLabel(QtWidgets.QLabel):
    """Simple label that renders a playing card value."""

    def __init__(self, text: str = "??", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(48)
        self.setStyleSheet("border: 1px solid #666; padding: 6px; background: #fff; font-weight: bold;")


__all__ = ["CardLabel"]
