from __future__ import annotations

import sys

def confirm_process_termination(message: str, mode: str = "gui") -> bool:
    """
    Returns True only when user explicitly confirms process termination.
    mode="gui": GUI prompt first, then console fallback.
    mode="console": console-only prompt.
    """
    normalized_mode = mode.strip().lower()
    if normalized_mode == "console":
        return _confirm_console(message)

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        result = messagebox.askyesno("codexSync Confirmation", message, parent=root)
        root.destroy()
        return bool(result)
    except Exception:
        return _confirm_console(message)


def _confirm_console(message: str) -> bool:
    prompt = (
        f"{message}\n\n"
        "Type YES to terminate processes, or NO to cancel: "
    )
    if not sys.stdin or not sys.stdin.isatty():
        return False
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return False
    return answer in {"yes", "y"}
