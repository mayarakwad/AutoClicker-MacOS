"""Main window (tkinter). Drives the click engine; contains no clicking logic."""
import queue
import tkinter as tk
from tkinter import ttk

from engine import ClickConfig, ClickEngine
from hotkeys import HotkeyListener
from mouse_io import PointPicker, on_screen

# How often the window checks hotkey events and engine status.
POLL_MS = 50
# How often the pick tooltip follows the cursor.
TIP_MS = 30

BUTTON_NAMES = ["Left", "Right", "Middle"]
CLICK_TYPES = ["Single", "Double"]
RUNNING_COLOR = "#107c10"
ERROR_COLOR = "#c42b1c"


def _is_digits(text):
    """Entry validator: allow only empty text or up to 9 ASCII digits."""
    return text == "" or (len(text) <= 9 and text.isascii() and text.isdigit())


def _is_coordinate(text):
    """Entry validator for X/Y: digits with an optional leading minus.

    Screens left of or above the main one have negative coordinates.
    """
    return len(text) <= 7 and _is_digits(text.removeprefix("-"))


def _set_enabled(widget, enabled):
    widget.state(["!disabled" if enabled else "disabled"])


class App:
    def __init__(self, root):
        self.root = root
        self.engine = ClickEngine()
        self.error = ""
        self.picker = None
        self.tip = None
        # Hotkeys and the picker fire on pynput's threads; queue their events
        # as tuples so tkinter is only touched from the main thread.
        self.events = queue.Queue()
        self.hotkeys = HotkeyListener(
            on_toggle=lambda: self.events.put(("toggle",)),
            on_escape=lambda: self.events.put(("escape",)),
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
        coordinate = (root.register(_is_coordinate), "%P")

        def number_entry(parent, var, validate=digits):
            return ttk.Entry(parent, textvariable=var, width=6, justify="right",
                             validate="key", validatecommand=validate)

        box = ttk.LabelFrame(outer, text="Click interval", padding=(10, 6))
        box.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.hours = tk.StringVar(value="0")
        self.mins = tk.StringVar(value="0")
        self.secs = tk.StringVar(value="0")
        self.millis = tk.StringVar(value="100")
        fields = ((self.hours, "hours"), (self.mins, "mins"), (self.secs, "secs"), (self.millis, "milliseconds"))
        for i, (var, label) in enumerate(fields):
            number_entry(box, var).grid(row=0, column=i * 2, padx=(0 if i == 0 else 10, 4))
            ttk.Label(box, text=label).grid(row=0, column=i * 2 + 1, sticky="w")
        row = ttk.Frame(box)
        row.grid(row=1, column=0, columnspan=8, sticky="w", pady=(6, 0))
        self.use_offset = tk.BooleanVar(value=False)
        self.offset = tk.StringVar(value="40")
        ttk.Checkbutton(row, text="Random offset ±", variable=self.use_offset).grid(row=0, column=0)
        self.offset_entry = number_entry(row, self.offset)
        self.offset_entry.grid(row=0, column=1, padx=4)
        ttk.Label(row, text="milliseconds").grid(row=0, column=2)

        box = ttk.LabelFrame(outer, text="Click options", padding=(10, 6))
        box.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(8, 0))
        self.button = tk.StringVar(value="Left")
        self.click_type = tk.StringVar(value="Single")
        combos = (("Mouse button:", self.button, BUTTON_NAMES), ("Click type:", self.click_type, CLICK_TYPES))
        for i, (label, var, values) in enumerate(combos):
            ttk.Label(box, text=label).grid(row=i, column=0, sticky="w", pady=2)
            ttk.Combobox(box, textvariable=var, values=values, state="readonly",
                         width=8).grid(row=i, column=1, padx=(8, 0), pady=2)

        box = ttk.LabelFrame(outer, text="Click repeat", padding=(10, 6))
        box.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(8, 0))
        self.repeat_mode = tk.StringVar(value="forever")
        self.repeat_count = tk.StringVar(value="1")
        ttk.Radiobutton(box, text="Repeat", value="count",
                        variable=self.repeat_mode).grid(row=0, column=0, sticky="w", pady=2)
        self.repeat_entry = number_entry(box, self.repeat_count)
        self.repeat_entry.grid(row=0, column=1, padx=4)
        ttk.Label(box, text="times").grid(row=0, column=2, sticky="w")
        ttk.Radiobutton(box, text="Repeat until stopped", value="forever",
                        variable=self.repeat_mode).grid(row=1, column=0, columnspan=3, sticky="w", pady=2)

        box = ttk.LabelFrame(outer, text="Cursor position", padding=(10, 6))
        box.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.position_mode = tk.StringVar(value="current")
        self.x = tk.StringVar(value="0")
        self.y = tk.StringVar(value="0")
        ttk.Radiobutton(box, text="Current location", value="current",
                        variable=self.position_mode).grid(row=0, column=0, padx=(0, 16))
        ttk.Radiobutton(box, value="pick", variable=self.position_mode).grid(row=0, column=1)
        self.pick_button = ttk.Button(box, text="Pick location", command=self.pick_location)
        self.pick_button.grid(row=0, column=2, padx=(0, 10))
        ttk.Label(box, text="X").grid(row=0, column=3)
        self.x_entry = number_entry(box, self.x, coordinate)
        self.x_entry.grid(row=0, column=4, padx=(4, 10))
        ttk.Label(box, text="Y").grid(row=0, column=5)
        self.y_entry = number_entry(box, self.y, coordinate)
        self.y_entry.grid(row=0, column=6, padx=(4, 0))

        key = self.hotkeys.hotkey.upper()
        self.start_button = ttk.Button(outer, text=f"Start ({key})", command=self.start)
        self.start_button.grid(row=3, column=0, sticky="ew", padx=(0, 4), pady=(10, 0), ipady=6)
        self.stop_button = ttk.Button(outer, text=f"Stop ({key})", command=self.stop)
        self.stop_button.grid(row=3, column=1, sticky="ew", padx=(4, 0), pady=(10, 0), ipady=6)

        self.status = ttk.Label(outer, anchor="w")
        self.status.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        # Traces (not widget commands) so entries also follow values set in code.
        for var in (self.use_offset, self.repeat_mode, self.position_mode):
            var.trace_add("write", lambda *_: self._sync_inputs())
        self._sync_inputs()
        self._refresh()

    def _sync_inputs(self):
        """Enable each entry only while the option it belongs to is selected."""
        _set_enabled(self.offset_entry, self.use_offset.get())
        _set_enabled(self.repeat_entry, self.repeat_mode.get() == "count")
        picked = self.position_mode.get() == "pick"
        _set_enabled(self.x_entry, picked)
        _set_enabled(self.y_entry, picked)

    @staticmethod
    def _number(var, name):
        text = var.get().strip()
        if not text:
            raise ValueError(f"{name} can't be empty")
        try:
            return int(text)
        except ValueError:
            raise ValueError(f"{name} must be a number") from None

    def _read_config(self):
        """Build a ClickConfig from the inputs; ValueError carries the message to show."""
        interval = (self._number(self.hours, "Hours") * 3_600_000
                    + self._number(self.mins, "Mins") * 60_000
                    + self._number(self.secs, "Secs") * 1000
                    + self._number(self.millis, "Milliseconds"))
        if interval < 1:
            raise ValueError("Interval must be at least 1 ms")
        offset = self._number(self.offset, "Random offset") if self.use_offset.get() else 0
        repeat = 0
        if self.repeat_mode.get() == "count":
            repeat = self._number(self.repeat_count, "Repeat count")
            if repeat < 1:
                raise ValueError("Repeat count must be at least 1")
        position = None
        if self.position_mode.get() == "pick":
            position = (self._number(self.x, "X"), self._number(self.y, "Y"))
            if not on_screen(*position):
                raise ValueError(f"Location {position[0]}, {position[1]} is not on any screen")
        return ClickConfig(interval_ms=interval, random_offset_ms=offset,
                           button=self.button.get().lower(), double=self.click_type.get() == "Double",
                           repeat=repeat, position=position)

    def start(self):
        if self.engine.running or self.picker is not None:
            return
        try:
            self.engine.start(self._read_config())
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

    def pick_location(self):
        """Hide the window; the next left click anywhere sets X/Y (Esc cancels)."""
        if self.engine.running or self.picker is not None:
            return
        self.picker = PointPicker(on_pick=lambda x, y: self.events.put(("picked", x, y)))
        self.picker.start()
        self.root.withdraw()
        self.tip = tk.Toplevel(self.root)
        self.tip.overrideredirect(True)
        self.tip.attributes("-topmost", True)
        self.tip_label = tk.Label(self.tip, background="#ffffe1", relief="solid", borderwidth=1,
                                  padx=6, pady=3, justify="left")
        self.tip_label.pack()
        self._follow_cursor()

    def _follow_cursor(self):
        if self.tip is None:
            return
        x, y = self.root.winfo_pointerxy()
        self.tip_label.config(text=f"X {x}   Y {y}\nClick to pick this point · Esc to cancel")
        self.tip.geometry(f"+{x + 16}+{y + 20}")
        self.root.after(TIP_MS, self._follow_cursor)

    def _end_pick(self, point=None):
        self.picker.stop()
        self.picker = None
        self.tip.destroy()
        self.tip = None
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        if point is not None:
            self.x.set(str(point[0]))
            self.y.set(str(point[1]))
            self.position_mode.set("pick")

    def close(self):
        if self.picker is not None:
            self.picker.stop()
        self.engine.stop()
        self.hotkeys.stop()
        self.root.destroy()

    def _poll(self):
        while True:
            try:
                kind, *args = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "picked" and self.picker is not None:
                self._end_pick(args)
            elif kind == "escape" and self.picker is not None:
                self._end_pick()
            elif kind == "escape" and self.engine.running:
                self.stop("Esc pressed")
            elif kind == "toggle" and self.picker is None:
                self.toggle()
        self._refresh()
        self.root.after(POLL_MS, self._poll)

    def _refresh(self):
        running = self.engine.running
        self.start_button.state(["disabled" if running else "!disabled"])
        self.stop_button.state(["!disabled" if running else "disabled"])
        _set_enabled(self.pick_button, not running)
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
