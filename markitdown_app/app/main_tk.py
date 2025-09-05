from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk

from markitdown_app.ui.tkinter.gui import TkApp


def main() -> None:
    root = tk.Tk()
    try:
        azure_path = os.path.join(os.path.dirname(__file__), "..", "ui", "tkinter", "resources", "azure.tcl")
        root.call("source", os.path.abspath(azure_path))
    except Exception:
        pass
    root.title("MarkURLdown (Tk)")
    # 默认更大的窗口尺寸，并设置一个合理的最小尺寸
    try:
        root.geometry("920x560")
        root.minsize(800, 480)
    except Exception:
        pass
    style = ttk.Style()
    try:
        style.configure("Accent.TButton", font=("TkDefaultFont", 11, "bold"), padding=(20, 8))
    except Exception:
        pass
    TkApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()


