"""mouse_io tests that don't send any input."""
import unittest

from mouse_io import normalize, on_screen


class NormalizeTest(unittest.TestCase):
    def test_round_trips_to_the_same_pixel(self):
        # Windows maps n back to a pixel as n * size // 65536.
        for origin, size in ((0, 1920), (0, 1080), (-1920, 3840), (-1440, 2520), (0, 7680)):
            for value in range(origin, origin + size):
                n = normalize(value, origin, size)
                self.assertLessEqual(n, 65535)
                self.assertEqual(n * size // 65536 + origin, value)


class OnScreenTest(unittest.TestCase):
    def test_main_screen_origin_is_on_screen(self):
        self.assertTrue(on_screen(0, 0))

    def test_far_away_point_is_not(self):
        self.assertFalse(on_screen(-99999, -99999))


if __name__ == "__main__":
    unittest.main()
