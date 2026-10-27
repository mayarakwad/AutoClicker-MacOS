"""Engine tests. They use a fake mouse, so nothing is really clicked.

Run from the project folder:  python -m unittest
"""
import time
import unittest

from pynput.mouse import Button

from engine import ClickConfig, ClickEngine


class FakeMouse:
    def __init__(self):
        self.position = (500, 500)
        self.clicked = []

    def click(self, button, count=1):
        self.clicked.append((button, count))


class ClickEngineTest(unittest.TestCase):
    def setUp(self):
        self.mouse = FakeMouse()
        self.engine = ClickEngine(mouse=self.mouse)

    def tearDown(self):
        self.engine.stop()
        self.engine.join(1)

    def test_clicks_at_interval(self):
        self.engine.start(ClickConfig(interval_ms=20))
        time.sleep(0.5)
        self.engine.stop()
        self.engine.join(1)
        # 0.5 s / 20 ms = 25 clicks; allow for timer jitter.
        self.assertGreaterEqual(self.engine.clicks, 20)
        self.assertLessEqual(self.engine.clicks, 26)
        self.assertEqual(self.engine.clicks, len(self.mouse.clicked))

    def test_stop_is_quick_with_long_interval(self):
        self.engine.start(ClickConfig(interval_ms=10_000))
        time.sleep(0.1)
        started = time.perf_counter()
        self.engine.stop()
        self.engine.join(1)
        self.assertFalse(self.engine.running)
        self.assertLess(time.perf_counter() - started, 0.2)
        self.assertEqual(self.engine.clicks, 0)

    def test_uses_chosen_button(self):
        self.engine.start(ClickConfig(interval_ms=5, button="right"))
        time.sleep(0.1)
        self.engine.stop()
        self.engine.join(1)
        self.assertTrue(self.mouse.clicked)
        self.assertTrue(all(b == Button.right for b, _ in self.mouse.clicked))

    def test_failsafe_corner_stops_clicking(self):
        self.engine.start(ClickConfig(interval_ms=10))
        time.sleep(0.1)
        self.mouse.position = (1, 0)
        self.engine.join(1)
        self.assertFalse(self.engine.running)
        self.assertEqual(self.engine.stop_reason, "mouse in top-left corner")
        clicks = self.engine.clicks
        time.sleep(0.1)
        self.assertEqual(self.engine.clicks, clicks)

    def test_stop_reason_is_kept(self):
        self.engine.start(ClickConfig(interval_ms=10))
        self.engine.stop("Esc pressed")
        self.engine.join(1)
        self.assertEqual(self.engine.stop_reason, "Esc pressed")

    def test_rejects_bad_config(self):
        with self.assertRaises(ValueError):
            self.engine.start(ClickConfig(interval_ms=0))
        with self.assertRaises(ValueError):
            self.engine.start(ClickConfig(button="side"))
        self.assertFalse(self.engine.running)


if __name__ == "__main__":
    unittest.main()
