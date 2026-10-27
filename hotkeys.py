"""Global hotkeys: work even when the window is minimized or not focused."""
from pynput import keyboard


def key_name(key):
    """Return a stable lowercase name for a pynput key, e.g. 'f6', 'esc', 'a'."""
    if isinstance(key, keyboard.Key):
        return key.name
    char = getattr(key, "char", None)
    if char:
        return char.lower()
    vk = getattr(key, "vk", None)
    return f"vk{vk}" if vk is not None else None


class HotkeyListener:
    """Calls `on_toggle` for the start/stop key and `on_escape` for Esc.

    Keys are only observed, never blocked, so other apps still receive them.
    Callbacks run on pynput's listener thread and must not touch tkinter.
    """

    def __init__(self, on_toggle, on_escape, hotkey="f6"):
        self.hotkey = hotkey
        self._on_toggle = on_toggle
        self._on_escape = on_escape
        self._held = set()
        self._listener = None

    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener is not None:
            self._listener.stop()

    def _on_press(self, key):
        name = key_name(key)
        if name is None or name in self._held:
            return  # ignore auto-repeat while the key is held down
        self._held.add(name)
        if name == self.hotkey:
            self._on_toggle()
        elif name == "esc":
            self._on_escape()

    def _on_release(self, key):
        self._held.discard(key_name(key))
