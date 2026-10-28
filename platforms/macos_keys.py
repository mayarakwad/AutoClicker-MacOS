"""macOS key codes -> the app's key names (the same names Windows uses).

Pure Python, so it can be tested on any OS. Key codes are physical key
positions on an ANSI keyboard (Carbon's kVK_* values from Events.h), so
letters follow the key's position, not the active keyboard layout.
"""
_LETTERS_AND_DIGITS = {
    0x00: "a", 0x01: "s", 0x02: "d", 0x03: "f", 0x04: "h", 0x05: "g", 0x06: "z", 0x07: "x",
    0x08: "c", 0x09: "v", 0x0B: "b", 0x0C: "q", 0x0D: "w", 0x0E: "e", 0x0F: "r", 0x10: "y",
    0x11: "t", 0x12: "1", 0x13: "2", 0x14: "3", 0x15: "4", 0x16: "6", 0x17: "5", 0x19: "9",
    0x1A: "7", 0x1C: "8", 0x1D: "0", 0x1F: "o", 0x20: "u", 0x22: "i", 0x23: "p", 0x25: "l",
    0x26: "j", 0x28: "k", 0x2D: "n", 0x2E: "m",
}
_FUNCTION_KEYS = {
    0x7A: "f1", 0x78: "f2", 0x63: "f3", 0x76: "f4", 0x60: "f5", 0x61: "f6", 0x62: "f7",
    0x64: "f8", 0x65: "f9", 0x6D: "f10", 0x67: "f11", 0x6F: "f12", 0x69: "f13", 0x6B: "f14",
    0x71: "f15", 0x6A: "f16", 0x40: "f17", 0x4F: "f18", 0x50: "f19", 0x5A: "f20",
}
_KEYPAD = {
    0x52: "num0", 0x53: "num1", 0x54: "num2", 0x55: "num3", 0x56: "num4", 0x57: "num5",
    0x58: "num6", 0x59: "num7", 0x5B: "num8", 0x5C: "num9", 0x41: "num_decimal",
    0x43: "num_multiply", 0x45: "num_add", 0x4B: "num_divide", 0x4E: "num_subtract",
    0x47: "num_lock",  # Clear sits where Num Lock is on a PC keypad
    0x4C: "enter",     # keypad Enter, named like Windows does
}
_OTHER = {
    0x24: "enter", 0x30: "tab", 0x31: "space", 0x33: "backspace", 0x35: "esc",
    0x39: "caps_lock", 0x72: "insert",  # Help sits where Insert is on a PC keyboard
    0x73: "home", 0x74: "page_up", 0x75: "delete", 0x77: "end", 0x79: "page_down",
    0x7B: "left", 0x7C: "right", 0x7D: "down", 0x7E: "up",
    # Modifiers ('win' is Command); they normally arrive as flag changes.
    0x37: "win", 0x36: "win", 0x38: "shift", 0x3C: "shift",
    0x3A: "alt", 0x3D: "alt", 0x3B: "ctrl", 0x3E: "ctrl",
}
KEYCODE_NAMES = {**_LETTERS_AND_DIGITS, **_FUNCTION_KEYS, **_KEYPAD, **_OTHER}

# CGEventFlags bits (kCGEventFlagMask*), in the app's modifier names.
FLAG_MODIFIERS = ((0x40000, "ctrl"), (0x80000, "alt"), (0x20000, "shift"), (0x100000, "win"))


def key_name(keycode):
    """Name for a macOS key code; unnamed keys (punctuation etc.) become 'vk<code>'."""
    return KEYCODE_NAMES.get(keycode, f"vk{keycode}")


KEY_NAMES = {key_name(code) for code in range(128)}


def modifiers_from_flags(flags):
    return {name for mask, name in FLAG_MODIFIERS if flags & mask}
