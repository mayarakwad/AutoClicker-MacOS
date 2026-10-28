"""macOS key code tests. Pure Python, so they run on any OS."""
import unittest

from hotkeys import DEFAULT_HOTKEY, MODIFIER_ORDER
from platforms.macos_keys import KEY_NAMES, KEYCODE_NAMES, key_name, modifiers_from_flags


class MacKeyNamesTest(unittest.TestCase):
    def test_known_keys(self):
        self.assertEqual(key_name(0x00), "a")
        self.assertEqual(key_name(0x2E), "m")
        self.assertEqual(key_name(0x1D), "0")
        self.assertEqual(key_name(0x61), "f6")
        self.assertEqual(key_name(0x7A), "f1")
        self.assertEqual(key_name(0x5A), "f20")
        self.assertEqual(key_name(0x35), "esc")
        self.assertEqual(key_name(0x57), "num5")
        self.assertEqual(key_name(0x74), "page_up")

    def test_unnamed_keys_get_codes(self):
        self.assertEqual(key_name(0x2C), "vk44")  # '/' key

    def test_every_letter_digit_and_f_key_once(self):
        names = list(KEYCODE_NAMES.values())
        for name in [chr(c) for c in range(ord("a"), ord("z") + 1)] + [str(d) for d in range(10)]:
            self.assertEqual(names.count(name), 1, name)
        for n in range(1, 21):
            self.assertEqual(names.count(f"f{n}"), 1, f"f{n}")
        for n in range(10):
            self.assertEqual(names.count(f"num{n}"), 1, f"num{n}")

    def test_names_the_hotkey_logic_relies_on_exist(self):
        for name in (DEFAULT_HOTKEY, "esc", "space", "enter", "tab", "backspace", *MODIFIER_ORDER):
            self.assertIn(name, KEY_NAMES)

    def test_modifiers_from_flags(self):
        self.assertEqual(modifiers_from_flags(0), set())
        self.assertEqual(modifiers_from_flags(0x100000 | 0x20000), {"win", "shift"})
        self.assertEqual(modifiers_from_flags(0x40000 | 0x80000 | 0x100), {"ctrl", "alt"})


if __name__ == "__main__":
    unittest.main()
