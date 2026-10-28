"""Real Quartz checks that need no permission and send no input (macOS only)."""
import sys
import unittest

if sys.platform == "darwin":
    from platforms import macos


@unittest.skipUnless(sys.platform == "darwin", "macOS backend")
class RealQuartzTest(unittest.TestCase):
    def test_cursor_position_is_whole_points(self):
        x, y = macos.Mouse().position
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)

    def test_on_screen(self):
        self.assertTrue(macos.on_screen(0, 0))
        self.assertFalse(macos.on_screen(-99999, -99999))

    def test_is_own_window_off_screen(self):
        self.assertFalse(macos.is_own_window(-99999, -99999))

    def test_reading_settings_does_not_fail(self):
        self.assertIn(macos.system_uses_dark(), (True, False))
        problem = macos.permission_problem()
        self.assertTrue(problem is None or "Privacy & Security" in problem)


if __name__ == "__main__":
    unittest.main()
