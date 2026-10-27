"""Main window (tkinter). Drives the click engine; contains no clicking logic."""
import queue
import tkinter as tk
from tkinter import ttk

from engine import ClickConfig, ClickEngine
from hotkeys import HotkeyListener

# How often the window checks hotkey events and engine status.
POLL_MS = 50

BUTTON_NAMES = ["Left", "Right", "Middle"]
RUNNING_COLOR = "#107c10"
ERROR_COLOR = "#c42b1c"


def _is_digits(text):
    """Entry validator: allow only empty text or up to 9 ASCII digits."""
    return text == "" or (len(text) <= 9 and text.isascii() and text.isdigit())


class App:
    def __init__(self, root):
        self.root = root
        self.engine = ClickEngine()
        self.error = ""
        # Hotkeys fire on pynput's thread; queue them so tkinter is only
        # touched from the main thread.
        self.events = queue.Queue()
        self.hotkeys = HotkeyListener(
            on_toggle=lambda: self.events.put("toggle"),
            on_escape=lambda: self.events.put("escape"),
        )
        self._build()
        self.hotkeys.start()
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._poll()

    def _build(self):
        root = self.root
        root.title("AutoClicker")
        root.resizable(False, False)

        outer = ttk.Frame(root, padding=10)
        outer.grid()
        outer.columnconfigure((0, 1), weight=1, uniform="half")
        digits = (root.register(_is_digits), "%P")

        interval = ttk.LabelFrame(outer, text="Click interval", padding=(10, 6))
        interval.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.hours = tk.StringVar(value="0")
        self.mins = tk.StringVar(value="0")
        self.secs = tk.StringVar(value="0")
        self.millis = tk.StringVar(value="100")
        fields = ((self.hours, "hours"), (self.mins, "mins"), (self.secs, "secs"), (self.millis, "milliseconds"))
        for i, (var, label) in enumerate(fields):
            entry = ttk.Entry(interval, textvariable=var, width=6, justify="right",
                              validate="key", validatecommand=digits)
            entry.grid(row=0, column=i * 2, padx=(0 if i == 0 else 10, 4))
            ttk.Label(interval, text=label).grid(row=0, column=i * 2 + 1)

        options = ttk.LabelFrame(outer, text="Click options", padding=(10, 6))
        options.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Label(options, text="Mouse button:").grid(row=0, column=0, sticky="w")
        self.button = tk.StringVar(value="Left")
        ttk.Combobox(options, textvariable=self.button, values=BUTTON_NAMES,
                     state="readonly", width=10).grid(row=0, column=1, padx=(8, 0))

        key = self.hotkeys.hotkey.upper()
        self.start_button = ttk.Button(outer, text=f"Start ({key})", command=self.start)
        self.start_button.grid(row=2, column=0, sticky="ew", padx=(0, 4), pady=(10, 0), ipady=6)
        self.stop_button = ttk.Button(outer, text=f"Stop ({key})", command=self.stop)
        self.stop_button.grid(row=2, column=1, sticky="ew", padx=(4, 0), pady=(10, 0), ipady=6)

        self.status = ttk.Label(outer, anchor="w")
        self.status.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self._refresh()

    def _interval_ms(self):
        total = 0
        units = ((self.hours, 3_600_000, "Hours"), (self.mins, 60_000, "Mins"),
                 (self.secs, 1000, "Secs"), (self.millis, 1, "Milliseconds"))
        for var, unit_ms, name in units:
            text = var.get().strip()
            if not text:
                raise ValueError(f"{name} can't be empty")
            total += int(text) * unit_ms
        if total < 1:
            raise ValueError("Interval must be at least 1 ms")
        return total

    def start(self):
        if self.engine.running:
            return
        try:
            config = ClickConfig(interval_ms=self._interval_ms(), button=self.button.get().lower())
            self.engine.start(config)
        except ValueError as e:
            self.error = str(e)
            self.root.bell()
        else:
            self.error = ""
        self._refresh()

    def stop(self, reason=""):
        self.engine.stop(reason)
        self.error = ""
        self._refresh()

    def toggle(self):
        if self.engine.running:
            self.stop()
        else:
            self.start()

    def close(self):
        self.engine.stop()
        self.hotkeys.stop()
        self.root.destroy()

    def _poll(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "toggle":
                self.toggle()
            elif event == "escape" and self.engine.running:
                self.stop("Esc pressed")
        self._refresh()
        self.root.after(POLL_MS, self._poll)

    def _refresh(self):
        running = self.engine.running
        self.start_button.state(["disabled" if running else "!disabled"])
        self.stop_button.state(["!disabled" if running else "disabled"])
        if self.error and not running:
            self.status.config(text=self.error, foreground=ERROR_COLOR)
            return
        n = self.engine.clicks
        clicks = f"{n:,} click" + ("" if n == 1 else "s")
        if running:
            self.status.config(text=f"Running · {clicks}", foreground=RUNNING_COLOR)
        elif self.engine.stop_reason:
            self.status.config(text=f"Stopped ({self.engine.stop_reason}) · {clicks}", foreground="")
        else:
            self.status.config(text=f"Stopped · {clicks}", foreground="")
