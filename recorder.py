"""Click recording: captures clicks anywhere on screen as engine Steps.

Also converts steps to and from the plain dicts stored in the settings file.
"""
import time
from dataclasses import asdict

from pynput import mouse

from engine import BUTTONS, Step
from mouse_io import is_own_window

_BUTTON_NAMES = {button: name for name, button in BUTTONS.items()}


class ClickRecorder:
    """Records each button press as a Step (button, position, delay since the
    previous press, or since start() for the first).

    Presses on this app's own windows (e.g. its Stop button) are skipped.
    `on_step(step)` runs on pynput's listener thread and must not touch tkinter.
    """

    def __init__(self, on_step, is_own=is_own_window):
        self._on_step = on_step
        self._is_own = is_own
        self._last = time.perf_counter()
        self._listener = mouse.Listener(on_click=self._on_click)
        self._listener.daemon = True

    def start(self):
        self._last = time.perf_counter()
        self._listener.start()

    def stop(self):
        self._listener.stop()

    def _on_click(self, x, y, button, pressed):
        if not pressed or button not in _BUTTON_NAMES or self._is_own(x, y):
            return
        now = time.perf_counter()
        delay_ms = max(1, round((now - self._last) * 1000))
        self._last = now
        self._on_step(Step(delay_ms, _BUTTON_NAMES[button], x, y))


def dump_steps(steps):
    return [asdict(step) for step in steps]


def load_steps(data):
    """Steps from settings data; [] if anything about it is invalid."""
    if not isinstance(data, list):
        return []
    steps = []
    for item in data:
        if not isinstance(item, dict) or set(item) != {"delay_ms", "button", "x", "y"}:
            return []
        ints = (item["delay_ms"], item["x"], item["y"])
        if not all(type(v) is int for v in ints) or item["delay_ms"] < 1 or item["button"] not in BUTTONS:
            return []
        steps.append(Step(**item))
    return steps
