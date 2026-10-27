"""Global hotkeys: work even when the window is minimized or not focused.

Keys are named from their Windows virtual-key code ('f6', 'a', 'page_up'),
so a name doesn't change when Ctrl or Shift is held. A hotkey is a combo
string: modifiers in a fixed order, then the key ('ctrl+shift+f6').
"""
import ctypes

from pynput import keyboard

DEFAULT_HOTKEY = "f6"
MODIFIER_ORDER = ("ctrl", "alt", "shift", "win")
_MODIFIER_VKS = {"ctrl": (0x11, 0xA2, 0xA3), "alt": (0x12, 0xA4, 0xA5),
                 "shift": (0x10, 0xA0, 0xA1), "win": (0x5B, 0x5C)}
_VK_MODIFIER = {vk: name for name, vks in _MODIFIER_VKS.items() for vk in vks}
_SPECIAL = {
    0x08: "backspace", 0x09: "tab", 0x0D: "enter", 0x13: "pause", 0x14: "caps_lock",
    0x1B: "esc", 0x20: "space", 0x21: "page_up", 0x22: "page_down", 0x23: "end",
    0x24: "home", 0x25: "left", 0x26: "up", 0x27: "right", 0x28: "down",
    0x2C: "print_screen", 0x2D: "insert", 0x2E: "delete", 0x5D: "menu",
    0x6A: "num_multiply", 0x6B: "num_add", 0x6D: "num_subtract", 0x6E: "num_decimal",
    0x6F: "num_divide", 0x90: "num_lock", 0x91: "scroll_lock",
}
# Keys you type with: alone as a hotkey they'd fire mid-sentence, because
# keys are never blocked from other apps.
_TYPING_KEYS = {"space", "enter", "tab", "backspace"}

_user32 = ctypes.WinDLL("user32")
_user32.GetAsyncKeyState.restype = ctypes.c_short


def vk_name(vk):
    if vk in _VK_MODIFIER:
        return _VK_MODIFIER[vk]
    if 0x70 <= vk <= 0x87:
        return f"f{vk - 0x6F}"
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk).lower()
    if 0x60 <= vk <= 0x69:
        return f"num{vk - 0x60}"
    return _SPECIAL.get(vk, f"vk{vk}")


_KEY_NAMES = {vk_name(vk) for vk in range(1, 256)}


def key_name(key):
    """Name of a pynput key event, or None if it has no virtual-key code."""
    vk = key.value.vk if isinstance(key, keyboard.Key) else getattr(key, "vk", None)
    return vk_name(vk) if vk is not None else None


def make_combo(modifiers, key):
    return "+".join([m for m in MODIFIER_ORDER if m in modifiers] + [key])


def combo_problem(combo):
    """Why `combo` can't be the start/stop hotkey, or None if it's fine."""
    *mods, key = combo.split("+")
    if (key not in _KEY_NAMES or key in MODIFIER_ORDER
            or any(m not in MODIFIER_ORDER for m in mods) or make_combo(mods, key) != combo):
        return "Not a valid key"
    if key == "esc":
        return "Esc is reserved for the fail-safe"
    typing = len(key) == 1 or (key.startswith("num") and key[3:].isdigit()) or key in _TYPING_KEYS
    if typing and not {"ctrl", "alt"} & set(mods):
        return "Typing keys need Ctrl or Alt, or they'd fire while you type"
    return None


def display_name(combo):
    """'ctrl+page_up' -> 'Ctrl+Page Up'."""
    parts = []
    for name in combo.split("+"):
        if name.startswith("num") and name[3:].isdigit():
            parts.append(f"Num {name[3:]}")
        elif name.startswith("vk"):
            parts.append(f"Key {name[2:]}")
        else:
            parts.append(name.replace("_", " ").title())
    return "+".join(parts)


def held_modifiers():
    """Modifiers held right now, asked from Windows so a missed key-up
    (e.g. after Ctrl+Alt+Del or a UAC prompt) can't leave one stuck."""
    return {name for name, vks in _MODIFIER_VKS.items()
            if any(_user32.GetAsyncKeyState(vk) & 0x8000 for vk in vks)}


class HotkeyListener:
    """Calls `on_toggle` for the start/stop hotkey and `on_escape` for Esc.

    After record(on_record), the next key or combination goes to `on_record`
    instead of toggling; Esc still goes to `on_escape`. Keys are only
    observed, never blocked, so other apps still receive them. Callbacks run
    on pynput's listener thread and must not touch tkinter.
    """

    def __init__(self, on_toggle, on_escape, hotkey=DEFAULT_HOTKEY, modifiers=held_modifiers):
        self.hotkey = hotkey
        self._on_toggle = on_toggle
        self._on_escape = on_escape
        self._modifiers = modifiers
        self._on_record = None
        self._held = set()
        self._listener = None

    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener is not None:
            self._listener.stop()

    def record(self, on_record):
        self._on_record = on_record

    def stop_recording(self):
        self._on_record = None

    def _on_press(self, key):
        name = key_name(key)
        if name is None or name in self._held:
            return  # ignore auto-repeat while the key is held down
        self._held.add(name)
        if name in MODIFIER_ORDER:
            return
        if name == "esc":
            self._on_escape()
            return
        combo = make_combo(self._modifiers(), name)
        on_record, self._on_record = self._on_record, None
        if on_record is not None:
            on_record(combo)
        elif combo == self.hotkey:
            self._on_toggle()

    def _on_release(self, key):
        self._held.discard(key_name(key))
