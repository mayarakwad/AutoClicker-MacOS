"""Hotkey tests. Key events are fed in directly; no real keyboard hook."""
import unittest

from pynput.keyboard import Key, KeyCode

from hotkeys import HotkeyListener, combo_problem, display_name, key_name, make_combo


class KeyNameTest(unittest.TestCase):
    def test_special_keys(self):
        self.assertEqual(key_name(Key.f6), "f6")
        self.assertEqual(key_name(Key.f24), "f24")
        self.assertEqual(key_name(Key.page_up), "page_up")
        self.assertEqual(key_name(Key.esc), "esc")

    def test_left_and_right_modifiers_share_a_name(self):
        self.assertEqual(key_name(Key.ctrl_l), "ctrl")
        self.assertEqual(key_name(Key.ctrl_r), "ctrl")
        self.assertEqual(key_name(Key.alt_gr), "alt")
        self.assertEqual(key_name(Key.shift_r), "shift")
        self.assertEqual(key_name(Key.cmd), "win")

    def test_letters_come_from_vk_not_char(self):
        # With Ctrl held, Windows reports Ctrl+A's char as '\x01'.
        self.assertEqual(key_name(KeyCode(vk=0x41, char="\x01")), "a")
        self.assertEqual(key_name(KeyCode(vk=0x37, char="&")), "7")
        self.assertEqual(key_name(KeyCode.from_vk(0x65)), "num5")
        self.assertEqual(key_name(KeyCode.from_vk(0xBB)), "vk187")


class ComboTest(unittest.TestCase):
    def test_make_combo_orders_modifiers(self):
        self.assertEqual(make_combo({"shift", "ctrl"}, "f6"), "ctrl+shift+f6")
        self.assertEqual(make_combo(set(), "f6"), "f6")

    def test_valid_hotkeys(self):
        for combo in ("f6", "f24", "ctrl+shift+s", "alt+1", "page_down", "ctrl+num5", "insert", "shift+f8", "vk187"):
            self.assertIsNone(combo_problem(combo), combo)

    def test_esc_is_reserved(self):
        self.assertIn("fail-safe", combo_problem("esc"))
        self.assertIn("fail-safe", combo_problem("ctrl+esc"))

    def test_typing_keys_need_ctrl_or_alt(self):
        for combo in ("s", "shift+s", "1", "space", "enter", "num5"):
            self.assertIn("Ctrl or Alt", combo_problem(combo), combo)

    def test_malformed(self):
        for combo in ("", "ctrl", "foo", "shift+ctrl+f6", "ctrl+ctrl+f6", "hyper+f6", "f6+ctrl"):
            self.assertEqual(combo_problem(combo), "Not a valid key", combo)

    def test_display_name(self):
        self.assertEqual(display_name("f6"), "F6")
        self.assertEqual(display_name("ctrl+shift+f6"), "Ctrl+Shift+F6")
        self.assertEqual(display_name("page_up"), "Page Up")
        self.assertEqual(display_name("alt+num5"), "Alt+Num 5")
        self.assertEqual(display_name("ctrl+a"), "Ctrl+A")
        self.assertEqual(display_name("vk187"), "Key 187")


class HotkeyListenerTest(unittest.TestCase):
    def setUp(self):
        self.mods = set()
        self.events = []
        self.recorded = []
        self.listener = HotkeyListener(on_toggle=lambda: self.events.append("toggle"),
                                       on_escape=lambda: self.events.append("escape"),
                                       modifiers=lambda: self.mods)

    def tap(self, key):
        self.listener._on_press(key)
        self.listener._on_release(key)

    def test_hotkey_toggles(self):
        self.tap(Key.f6)
        self.tap(Key.f6)
        self.assertEqual(self.events, ["toggle", "toggle"])

    def test_auto_repeat_is_ignored(self):
        for _ in range(5):
            self.listener._on_press(Key.f6)
        self.listener._on_release(Key.f6)
        self.assertEqual(self.events, ["toggle"])

    def test_modifiers_must_match_exactly(self):
        self.listener.hotkey = "ctrl+f6"
        self.tap(Key.f6)
        self.mods = {"ctrl", "shift"}
        self.tap(Key.f6)
        self.assertEqual(self.events, [])
        self.mods = {"ctrl"}
        self.tap(Key.f6)
        self.assertEqual(self.events, ["toggle"])

    def test_plain_hotkey_ignores_modified_press(self):
        self.mods = {"ctrl"}
        self.tap(Key.f6)
        self.assertEqual(self.events, [])

    def test_escape_fires_with_any_modifiers(self):
        self.tap(Key.esc)
        self.mods = {"shift"}
        self.tap(Key.esc)
        self.assertEqual(self.events, ["escape", "escape"])

    def test_record_captures_next_combo_once(self):
        self.listener.record(self.recorded.append)
        self.tap(Key.ctrl_l)  # modifiers alone don't end recording
        self.mods = {"ctrl", "shift"}
        self.tap(KeyCode(vk=0x53, char="\x13"))
        self.assertEqual(self.recorded, ["ctrl+shift+s"])
        self.mods = set()
        self.tap(Key.f6)
        self.assertEqual(self.recorded, ["ctrl+shift+s"])
        self.assertEqual(self.events, ["toggle"])

    def test_recording_the_current_hotkey_does_not_toggle(self):
        self.listener.record(self.recorded.append)
        self.tap(Key.f6)
        self.assertEqual(self.recorded, ["f6"])
        self.assertEqual(self.events, [])

    def test_esc_while_recording_goes_to_escape(self):
        self.listener.record(self.recorded.append)
        self.tap(Key.esc)
        self.assertEqual(self.events, ["escape"])
        self.listener.stop_recording()
        self.tap(Key.f6)
        self.assertEqual(self.recorded, [])
        self.assertEqual(self.events, ["escape", "toggle"])


if __name__ == "__main__":
    unittest.main()
