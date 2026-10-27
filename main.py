"""AutoClicker entry point."""
import ctypes
import tkinter as tk

from ui import App


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
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
