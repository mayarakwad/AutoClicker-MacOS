"""Click engine: runs the clicking loop on a background thread.

Contains no UI code. The window starts and stops the engine and polls
`running`, `clicks` and `stop_reason` to show status. `clicks` counts click
actions, so a double click counts once.
"""
import random
import threading
import time
from dataclasses import dataclass

from pynput.mouse import Button

from mouse_io import Mouse

BUTTONS = {"left": Button.left, "right": Button.right, "middle": Button.middle}

# Fail-safe: the cursor within this many pixels of the main screen's
# top-left corner (0, 0) stops clicking.
FAILSAFE_MARGIN = 2

# Longest single sleep, so stop requests and the fail-safe are noticed
# quickly even when the interval is long.
POLL_SECONDS = 0.05


@dataclass
class ClickConfig:
    interval_ms: int = 100
    random_offset_ms: int = 0   # each delay is the interval ± up to this much
    button: str = "left"
    double: bool = False
    repeat: int = 0             # clicks before stopping; 0 = until stopped
    position: tuple = None      # (x, y) to click at; None = wherever the cursor is


def next_delay(config):
    """Seconds until the next click, with the random offset applied (never under 1 ms)."""
    ms = config.interval_ms
    if config.random_offset_ms:
        ms += random.randint(-config.random_offset_ms, config.random_offset_ms)
    return max(ms, 1) / 1000


class ClickEngine:
    def __init__(self, mouse=None):
        self._mouse = mouse or Mouse()
        self._thread = None
        self._stop_event = threading.Event()
        self.clicks = 0
        self.stop_reason = ""

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, config):
        if self.running:
            return
        if config.interval_ms < 1:
            raise ValueError("Interval must be at least 1 ms")
        if config.random_offset_ms < 0:
            raise ValueError("Random offset can't be negative")
        if config.repeat < 0:
            raise ValueError("Repeat count can't be negative")
        if config.button not in BUTTONS:
            raise ValueError(f"Unknown mouse button: {config.button!r}")
        self.clicks = 0
        self.stop_reason = ""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, args=(config,), daemon=True)
        self._thread.start()

    def stop(self, reason=""):
        """Ask the click thread to stop. `reason` is shown in the status line."""
        if self.running and not self._stop_event.is_set():
            self.stop_reason = reason
        self._stop_event.set()

    def join(self, timeout=None):
        if self._thread is not None:
            self._thread.join(timeout)

    def _run(self, config):
        button = BUTTONS[config.button]
        count = 2 if config.double else 1
        next_click = time.perf_counter() + next_delay(config)
        while self._wait_until(next_click):
            if config.position is None:
                self._mouse.click(button, count)
            else:
                self._mouse.click_at(*config.position, button, count)
            self.clicks += 1
            if config.repeat and self.clicks >= config.repeat:
                self.stop_reason = "finished"
                return
            next_click += next_delay(config)
            now = time.perf_counter()
            if next_click < now:
                # Fell behind (busy system): carry on from now instead of
                # firing a burst of clicks to catch up.
                next_click = now

    def _wait_until(self, deadline):
        """Sleep until `deadline`. Returns False if stopped or the fail-safe tripped."""
        while True:
            if self._stop_event.is_set():
                return False
            if self._in_failsafe_corner():
                self.stop_reason = "mouse in top-left corner"
                return False
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                return True
            # time.sleep uses a high-resolution timer on Windows (Python 3.11+),
            # so short intervals stay accurate even while the window is minimized.
            time.sleep(min(remaining, POLL_SECONDS))

    def _in_failsafe_corner(self):
        x, y = self._mouse.position
        return abs(x) <= FAILSAFE_MARGIN and abs(y) <= FAILSAFE_MARGIN
