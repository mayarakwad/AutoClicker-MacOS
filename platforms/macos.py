"""macOS backend: Quartz (CoreGraphics) through pyobjc.

Coordinates are points with the origin at the main display's top-left, the
same space Tk uses, so no DPI handling is needed.

Clicking needs Accessibility permission and watching the keyboard needs
Input Monitoring (System Settings > Privacy & Security). Without them macOS
silently drops clicks and key events, so permission_problem() tells the UI
what's missing, and event taps keep retrying until permission is granted.
"""
import os
import subprocess
import threading
import tkinter as tk
from pathlib import Path

import Foundation
import HIServices
import Quartz

from platforms.macos_keys import KEY_NAMES, key_name, modifiers_from_flags  # KEY_NAMES: re-exported

OS_NAME = "macOS"
NATIVE_THEME = "aqua"
NATIVE_DARK = True  # 'aqua' has its own dark appearance
MODIFIER_LABELS = {"ctrl": "Ctrl", "alt": "Option", "shift": "Shift", "win": "Cmd"}
TYPING_MODIFIERS = ("win", "ctrl", "alt")
EXAMPLE_COMBO = "win+shift+s"


# --- Process, files, look ---------------------------------------------------

def prepare_process():
    pass  # coordinates are already in points on every display


_activity = None  # NSProcessInfo token; App Nap stays off while it's held


def set_clicking(active):
    """While clicking, keep App Nap from delaying the click timer.

    App Nap throttles timers of apps whose windows are hidden or covered,
    which is exactly when an auto clicker runs (you're working in another app).
    """
    global _activity
    info = Foundation.NSProcessInfo.processInfo()
    if active and _activity is None:
        _activity = info.beginActivityWithOptions_reason_(
            Foundation.NSActivityUserInitiatedAllowingIdleSystemSleep | Foundation.NSActivityLatencyCritical,
            "Clicking on a timer")
    elif not active and _activity is not None:
        info.endActivity_(_activity)
        _activity = None


def set_app_icon(root, assets):
    """Dock icon when run from source; a built .app shows its bundle icon."""
    try:
        root.app_icon = tk.PhotoImage(master=root, file=assets / "app.png")
        root.iconphoto(True, root.app_icon)
    except tk.TclError:
        pass


def settings_folder():
    return Path.home() / "Library" / "Application Support" / "AutoClicker"


def system_uses_dark():
    """macOS's appearance (System Settings > Appearance)."""
    try:
        result = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"],
                                capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.stdout.strip() == "Dark"


def set_window_dark(window, dark):
    """Light or dark appearance for one window: title bar and native widgets."""
    try:
        window.tk.call("::tk::unsupported::MacWindowStyle", "appearance", window,
                       "darkaqua" if dark else "aqua")
    except tk.TclError:
        pass  # Tk before 8.6.10: windows simply follow the system appearance
    window.update_idletasks()


SOUNDS = {True: "/System/Library/Sounds/Tink.aiff", False: "/System/Library/Sounds/Pop.aiff"}


def play_sound(started):
    """Start/stop sound; afplay runs on its own, so the UI never waits."""
    try:
        subprocess.Popen(["afplay", SOUNDS[started]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def permission_problem():
    """What macOS still has to allow, as a status-line message; None if nothing."""
    missing = []
    if not HIServices.AXIsProcessTrusted():
        missing.append("Accessibility")
    if not Quartz.CGPreflightListenEventAccess():
        missing.append("Input Monitoring")
    if not missing:
        return None
    return ("Allow AutoClicker (or the terminal running it) in System Settings > "
            "Privacy & Security > " + " and ".join(missing))


def request_permissions():
    """Show macOS's own prompts for whatever is missing."""
    if not HIServices.AXIsProcessTrusted():
        HIServices.AXIsProcessTrustedWithOptions({HIServices.kAXTrustedCheckOptionPrompt: True})
    if not Quartz.CGPreflightListenEventAccess():
        Quartz.CGRequestListenEventAccess()


# --- Screens and windows ----------------------------------------------------

def on_screen(x, y):
    error, _, count = Quartz.CGGetDisplaysWithPoint((x, y), 1, None, None)
    return error == 0 and count > 0


def is_own_window(x, y):
    """Whether the frontmost window at (x, y) belongs to this app (e.g. its own Stop button)."""
    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID) or []
    for info in windows:  # front to back
        if info.get("kCGWindowAlpha", 1) == 0:
            continue
        ok, bounds = Quartz.CGRectMakeWithDictionaryRepresentation(info.get("kCGWindowBounds"), None)
        if ok and Quartz.CGRectContainsPoint(bounds, (x, y)):
            return info.get("kCGWindowOwnerPID") == os.getpid()
    return False


# --- Mouse output -----------------------------------------------------------

_BUTTONS = {  # name -> (down event, up event, CGMouseButton)
    "left": (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp, Quartz.kCGMouseButtonLeft),
    "right": (Quartz.kCGEventRightMouseDown, Quartz.kCGEventRightMouseUp, Quartz.kCGMouseButtonRight),
    "middle": (Quartz.kCGEventOtherMouseDown, Quartz.kCGEventOtherMouseUp, Quartz.kCGMouseButtonCenter),
}


def _post(event_type, x, y, button=Quartz.kCGMouseButtonLeft, click_state=None):
    event = Quartz.CGEventCreateMouseEvent(None, event_type, (x, y), button)
    if click_state is not None:
        Quartz.CGEventSetIntegerValueField(event, Quartz.kCGMouseEventClickState, click_state)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)


def _click(x, y, button, count):
    down, up, number = _BUTTONS[button]
    for n in range(1, count + 1):  # click state 1, 2: how macOS recognizes a double click
        _post(down, x, y, number, n)
        _post(up, x, y, number, n)


class Mouse:
    """Mouse output used by the click engine. Buttons are 'left', 'right', 'middle'.

    Posted events stay in order in one stream, so a click at a fixed point
    (move there, click, move back) lands there and the user keeps the
    cursor, which also keeps the top-left-corner fail-safe reachable.
    """

    @property
    def position(self):
        x, y = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
        return round(x), round(y)

    def click(self, button, count=1):
        _click(*self.position, button, count)

    def click_at(self, x, y, button, count=1):
        """Click at (x, y), then put the cursor back where it was."""
        home = self.position
        _post(Quartz.kCGEventMouseMoved, x, y)
        _click(x, y, button, count)
        _post(Quartz.kCGEventMouseMoved, *home)


# --- Event taps (mouse and keyboard input) ----------------------------------

_TAP_DISABLED = (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput)


class _EventTap:
    """A Quartz event tap on its own thread with its own run loop.

    handler(event_type, event) returns the event to let it through, or None
    to swallow it (only possible when not listen_only). If the tap can't be
    created yet (no permission), it retries every RETRY_SECONDS until
    stopped, so granting permission takes effect without a restart.
    """
    RETRY_SECONDS = 2

    def __init__(self, event_types, handler, listen_only):
        self._mask = 0
        for event_type in event_types:
            self._mask |= Quartz.CGEventMaskBit(event_type)
        self._handler = handler
        self._options = Quartz.kCGEventTapOptionListenOnly if listen_only else Quartz.kCGEventTapOptionDefault
        self._stopped = threading.Event()
        self._tap = None
        self._loop = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stopped.set()
        if self._loop is not None:
            Quartz.CFRunLoopStop(self._loop)

    def _run(self):
        while self._tap is None and not self._stopped.is_set():
            self._tap = Quartz.CGEventTapCreate(Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
                                                self._options, self._mask, self._callback, None)
            if self._tap is None:
                self._stopped.wait(self.RETRY_SECONDS)
        if self._tap is None:
            return
        source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        self._loop = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopAddSource(self._loop, source, Quartz.kCFRunLoopDefaultMode)
        Quartz.CGEventTapEnable(self._tap, True)
        while not self._stopped.is_set():
            Quartz.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, 0.5, False)
        Quartz.CGEventTapEnable(self._tap, False)

    def _callback(self, proxy, event_type, event, refcon):
        if event_type in _TAP_DISABLED:
            # macOS switches a tap off if a callback is too slow; switch it back on.
            Quartz.CGEventTapEnable(self._tap, True)
            return event
        try:
            return self._handler(event_type, event)
        except Exception:
            return event  # a bug here must never swallow the user's input


_DOWN_EVENTS = {down: name for name, (down, _, _) in _BUTTONS.items()}
MIDDLE_BUTTON_NUMBER = 2


class PointPicker:
    """Captures the next left click anywhere on screen and swallows it.

    `on_pick(x, y)` runs on the tap's thread and must not touch tkinter.
    """

    def __init__(self, on_pick):
        self._on_pick = on_pick
        self._picked = False
        self._tap = _EventTap((Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp),
                              self._handle, listen_only=False)

    def start(self):
        self._tap.start()

    def stop(self):
        self._tap.stop()

    def _handle(self, event_type, event):
        if event_type == Quartz.kCGEventLeftMouseDown and not self._picked:
            self._picked = True
            x, y = Quartz.CGEventGetLocation(event)
            self._on_pick(round(x), round(y))
            return None
        if event_type == Quartz.kCGEventLeftMouseUp and self._picked:
            self._tap.stop()
            return None
        return event


class MouseListener:
    """Left/right/middle presses anywhere: on_press(x, y, button_name).

    Listen-only, so clicks still reach the app underneath. Runs on the tap's thread.
    """

    def __init__(self, on_press):
        self._on_press = on_press
        self._tap = _EventTap(tuple(_DOWN_EVENTS), self._handle, listen_only=True)

    def start(self):
        self._tap.start()

    def stop(self):
        self._tap.stop()

    def _handle(self, event_type, event):
        name = _DOWN_EVENTS[event_type]
        if (name == "middle" and Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGMouseEventButtonNumber) != MIDDLE_BUTTON_NUMBER):
            return event  # side buttons also arrive as "other mouse" events
        x, y = Quartz.CGEventGetLocation(event)
        self._on_press(round(x), round(y), name)
        return event


class KeySource:
    """Global key events as names: on_press(name, modifiers), on_release(name).

    Listen-only, so keys still reach other apps. Modifiers come from the key
    event's own flags. Runs on the tap's thread. (Uses Quartz directly rather
    than pynput, whose keyboard listener crashes on recent macOS.)
    """

    def __init__(self, on_press, on_release):
        self._on_press = on_press
        self._on_release = on_release
        self._tap = _EventTap((Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp), self._handle, listen_only=True)

    def start(self):
        self._tap.start()

    def stop(self):
        self._tap.stop()

    def _handle(self, event_type, event):
        name = key_name(Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode))
        if event_type == Quartz.kCGEventKeyDown:
            self._on_press(name, modifiers_from_flags(Quartz.CGEventGetFlags(event)))
        else:
            self._on_release(name)
        return event
