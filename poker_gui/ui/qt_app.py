"""PyQt6 application bootstrap."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from PyQt6 import QtWidgets

from ..core.table_manager import DATA_PATH, TableManager, create_table_from_file, create_default_table
from .table import TableWindow


def _load_manager_via_dialog(parent: Optional[QtWidgets.QWidget]) -> Optional[tuple[TableManager, str]]:
    dialog = QtWidgets.QFileDialog(parent)
    dialog.setWindowTitle("Select Poker Table Configuration")
    dialog.setDirectory(str(DATA_PATH))
    dialog.setNameFilter("Config Files (*.json)")
    dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
    while True:
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None
        filenames = dialog.selectedFiles()
        if not filenames:
            return None
        path = Path(filenames[0])
        try:
            manager = create_table_from_file(path)
        except Exception as exc:  # pragma: no cover - GUI feedback
            QtWidgets.QMessageBox.critical(parent, "Failed to Load", str(exc))
            continue
        return manager, str(path)


def launch_qt(argv: Sequence[str]) -> int:
    app = QtWidgets.QApplication(list(argv))
    manager: Optional[TableManager] = None
    source: Optional[str] = None

    if len(argv) > 1:
        candidate = Path(argv[1]).expanduser()
        if candidate.exists():
            try:
                manager = create_table_from_file(candidate)
                source = str(candidate)
            except Exception as exc:  # pragma: no cover - GUI feedback
                QtWidgets.QMessageBox.critical(None, "Configuration Error", str(exc))
        else:
            QtWidgets.QMessageBox.warning(None, "Missing Configuration", f"Unable to open {candidate}.")

    if manager is None:
        result = _load_manager_via_dialog(None)
        if result is None:
            # As a final fallback, keep backward compatibility with bundled defaults.
            manager = create_default_table()
            source = "default settings"
        else:
            manager, source = result

    window = TableWindow(manager, source)
    window.show()
    return app.exec()


__all__ = ["launch_qt"]
