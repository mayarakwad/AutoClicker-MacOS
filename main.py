"""AutoClicker entry point."""
import ctypes
import sys
import tkinter as tk
from pathlib import Path

from ui import App

# Bundled files live next to this script, or in PyInstaller's unpack folder.
ASSETS = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets"


def enable_dpi_awareness():
    """Use real pixel coordinates on scaled (125%, 150%) displays.

    Must run before any window is created.
    """
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor aware
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    try:
        root.iconbitmap(default=ASSETS / "app.ico")  # default= covers dialogs too
    except tk.TclError:
        pass
    App(root)  # loads settings from %APPDATA%\AutoClicker\settings.json
    root.mainloop()


if __name__ == "__main__":
    main()
