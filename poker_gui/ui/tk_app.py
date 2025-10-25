"""Minimal Tkinter fallback UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..core.table_manager import TableManager


def launch_tk(manager: TableManager) -> int:
    root = tk.Tk()
    root.title("Hold'em Poker (Fallback)")
    status = tk.StringVar()

    def run_hand() -> None:
        manager.start_hand()
        winners = manager.state.resolve_showdown()
        text = "Winners: " + ", ".join(f"Seat {seat} +{amount}" for seat, amount in winners)
        status.set(text or "No winners")

    button = ttk.Button(root, text="Play Hand", command=run_hand)
    button.pack(padx=20, pady=20)
    ttk.Label(root, textvariable=status).pack(padx=20, pady=10)
    root.mainloop()
    return 0


__all__ = ["launch_tk"]
