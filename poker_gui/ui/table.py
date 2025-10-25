"""Qt widgets representing the poker table."""
from __future__ import annotations

from typing import List

from PyQt6 import QtCore, QtWidgets

from ..core.table_manager import TableManager
from .widgets import CardLabel


class TableWindow(QtWidgets.QMainWindow):
    def __init__(self, manager: TableManager) -> None:
        super().__init__()
        self.manager = manager
        self.setWindowTitle("Hold'em Poker")
        self.resize(1024, 720)
        self.view = TableView(manager)
        self.setCentralWidget(self.view)
        self.status = self.statusBar()
        self.status.showMessage("Welcome to Hold'em Poker")


class TableView(QtWidgets.QWidget):
    def __init__(self, manager: TableManager) -> None:
        super().__init__()
        self.manager = manager
        self._build_ui()
        self.manager.start_hand()
        self.update_view()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        header = QtWidgets.QHBoxLayout()
        self.table_label = QtWidgets.QLabel(self.manager.config.name)
        self.hand_label = QtWidgets.QLabel("Hand #0")
        header.addWidget(self.table_label)
        header.addStretch()
        header.addWidget(self.hand_label)
        layout.addLayout(header)

        self.board_layout = QtWidgets.QHBoxLayout()
        self.board_layout.setSpacing(8)
        layout.addLayout(self.board_layout)

        self.pot_label = QtWidgets.QLabel("Pot: 0")
        layout.addWidget(self.pot_label)

        self.players_table = QtWidgets.QTableWidget(0, 4)
        self.players_table.setHorizontalHeaderLabels(["Seat", "Name", "Stack", "Action"])
        self.players_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.players_table, stretch=1)

        self.message_label = QtWidgets.QLabel()
        layout.addWidget(self.message_label)

        controls = QtWidgets.QHBoxLayout()
        self.new_hand_btn = QtWidgets.QPushButton("New Hand")
        self.new_hand_btn.clicked.connect(self.on_new_hand)
        controls.addWidget(self.new_hand_btn)
        self.auto_play_btn = QtWidgets.QPushButton("Auto Play")
        self.auto_play_btn.clicked.connect(self.on_auto_play)
        controls.addWidget(self.auto_play_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.board_cards: List[CardLabel] = []
        for _ in range(5):
            label = CardLabel()
            self.board_layout.addWidget(label)
            self.board_cards.append(label)

    def update_view(self) -> None:
        self.hand_label.setText(f"Hand #{self.manager.hand_number}")
        board = self.manager.state.board
        for idx, label in enumerate(self.board_cards):
            if idx < len(board):
                label.setText(str(board[idx]))
            else:
                label.setText("??")
        pot_total = sum(self.manager.state.pot_manager.contributions.values())
        self.pot_label.setText(f"Pot: {pot_total}")
        self._update_players()

    def _update_players(self) -> None:
        players = self.manager.state.players
        self.players_table.setRowCount(len(players))
        for row, player in enumerate(players):
            self.players_table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(player.seat)))
            self.players_table.setItem(row, 1, QtWidgets.QTableWidgetItem(player.name))
            self.players_table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(player.stack)))
            last_action = next((action for action in reversed(self.manager.state.action_log) if action.seat == player.seat), None)
            self.players_table.setItem(row, 3, QtWidgets.QTableWidgetItem(last_action.move if last_action else ""))

    def on_new_hand(self) -> None:
        self.manager.start_hand()
        self.message_label.setText("New hand started")
        self.update_view()

    def on_auto_play(self) -> None:
        self.manager.start_hand()
        for _ in range(3):
            self._play_round()
            self.manager.state.move_to_next_street()
        self._play_round()
        winners = self.manager.state.resolve_showdown()
        if winners:
            text = ", ".join(f"Seat {seat}+{amount}" for seat, amount in winners)
        else:
            text = "No winners"
        self.message_label.setText(f"Showdown: {text}")
        self.update_view()

    def _play_round(self) -> None:
        for seat, player in enumerate(self.manager.state.players):
            if player.sitting_out:
                continue
            self.manager.play_ai_turn(seat)
        self.update_view()
        QtWidgets.QApplication.processEvents()


__all__ = ["TableWindow", "TableView"]
