"""Mouse input and output on Windows.

- Mouse: clicking for the engine. Clicks at the cursor go through pynput.
  Clicks at a fixed point are one SendInput batch (move there, click, move
  back), so the click can't land anywhere else and the user keeps the cursor,
  which also keeps the top-left-corner fail-safe reachable.
- PointPicker: captures the next left click anywhere on screen and swallows it.
- on_screen(): whether a point is on any monitor.

All coordinates are physical pixels (main.py makes the process DPI-aware).
"""
import ctypes
import ctypes.wintypes as wt

from pynput import mouse
from pynput.mouse import Button

user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE = 0x8000
BUTTON_FLAGS = {  # (down, up)
    Button.left: (0x0002, 0x0004),
    Button.right: (0x0008, 0x0010),
    Button.middle: (0x0020, 0x0040),
}
SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 76, 77, 78, 79
MONITOR_DEFAULTTONULL = 0
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class INPUT(ctypes.Structure):
    # The real INPUT holds a union; MOUSEINPUT is its largest member, so the
    # size and layout match.
    _fields_ = [("type", wt.DWORD), ("mi", MOUSEINPUT)]


user32.SendInput.argtypes = (wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wt.UINT
user32.MonitorFromPoint.argtypes = (wt.POINT, wt.DWORD)
user32.MonitorFromPoint.restype = wt.HMONITOR


def on_screen(x, y):
    return bool(user32.MonitorFromPoint(wt.POINT(x, y), MONITOR_DEFAULTTONULL))


def normalize(value, origin, size):
    """Pixel -> SendInput absolute coordinate (0..65535 across the virtual desktop).

    Windows maps back with n * size // 65536, so round up to land exactly
    on the requested pixel.
    """
    return ((value - origin) * 65536 + size - 1) // size


def _move(x, y):
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    return INPUT(INPUT_MOUSE, MOUSEINPUT(normalize(x, left, width), normalize(y, top, height), 0, flags, 0, 0))


def _button(flag):
    return INPUT(INPUT_MOUSE, MOUSEINPUT(0, 0, 0, flag, 0, 0))


def _send(inputs):
    user32.SendInput(len(inputs), (INPUT * len(inputs))(*inputs), ctypes.sizeof(INPUT))


class Mouse:
    """Mouse output used by the click engine."""

    def __init__(self):
        self._controller = mouse.Controller()

    @property
    def position(self):
        return self._controller.position

    def click(self, button, count=1):
        self._controller.click(button, count)

    def click_at(self, x, y, button, count=1):
        """Click at (x, y), then put the cursor back where it was."""
        home = self.position
        down, up = BUTTON_FLAGS[button]
        inputs = [_move(x, y)]
        for _ in range(count):
            inputs += [_button(down), _button(up)]
        inputs.append(_move(*home))
        # One batch: Windows won't interleave the user's own mouse input.
        _send(inputs)


class PointPicker:
    """Captures the next left click anywhere on screen and swallows it.

    `on_pick(x, y)` runs on pynput's hook thread and must not touch tkinter.
    """

    def __init__(self, on_pick):
        self._on_pick = on_pick
        self._picked = False
        self._listener = mouse.Listener(win32_event_filter=self._filter)
        self._listener.daemon = True

    def start(self):
        self._listener.start()

    def stop(self):
        self._listener.stop()

    def _filter(self, msg, data):
        if msg == WM_LBUTTONDOWN and not self._picked:
            self._picked = True
            self._on_pick(data.pt.x, data.pt.y)
            self._listener.suppress_event()
        elif msg == WM_LBUTTONUP and self._picked:
            self._listener.stop()
            self._listener.suppress_event()
