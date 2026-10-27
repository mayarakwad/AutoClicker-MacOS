"""Theme tests on a hidden Tk window."""
import tkinter as tk
import unittest
from tkinter import ttk
from unittest import mock

import theme


class ResolveTest(unittest.TestCase):
    def test_explicit_modes_pass_through(self):
        self.assertEqual(theme.resolve("light"), "light")
        self.assertEqual(theme.resolve("dark"), "dark")

    def test_system_follows_windows(self):
        with mock.patch("theme.windows_uses_dark", return_value=True):
            self.assertEqual(theme.resolve("system"), "dark")
        with mock.patch("theme.windows_uses_dark", return_value=False):
            self.assertEqual(theme.resolve("system"), "light")

    def test_reading_windows_setting_does_not_fail(self):
        self.assertIn(theme.windows_uses_dark(), (True, False))


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.combo = ttk.Combobox(self.root, values=["Left", "Right"], state="readonly")
        self.combo.grid()
        self.dialog = tk.Toplevel(self.root)
        self.dialog.withdraw()

    def tearDown(self):
        theme.apply(self.root, "light")
        self.root.destroy()

    def list_color(self):
        popdown = self.combo.tk.call("ttk::combobox::PopdownWindow", self.combo)
        return str(self.combo.tk.call(f"{popdown}.f.l", "cget", "-background"))

    def test_dark_then_light(self):
        theme.apply(self.root, "dark")
        self.assertEqual(ttk.Style(self.root).theme_use(), "clam")
        self.assertEqual(theme.current, "dark")
        self.assertEqual(theme.color("running"), theme.PALETTES["dark"]["running"])
        self.assertEqual(self.root.cget("background"), theme.BG)
        self.assertEqual(self.dialog.cget("background"), theme.BG)
        self.assertEqual(self.list_color(), theme.FIELD)

        theme.apply(self.root, "light")
        self.assertEqual(ttk.Style(self.root).theme_use(), "vista")
        self.assertEqual(theme.color("running"), theme.PALETTES["light"]["running"])
        self.assertEqual(self.list_color(), "SystemWindow")


if __name__ == "__main__":
    unittest.main()
