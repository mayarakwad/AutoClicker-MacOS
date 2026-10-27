"""Sound tests with winsound.Beep replaced, so nothing is played."""
import time
import unittest
from unittest import mock

import sounds


class SoundsTest(unittest.TestCase):
    def play_and_collect(self, started):
        with mock.patch("sounds.winsound.Beep") as beep:
            began = time.perf_counter()
            sounds.play(started)
            returned_after = time.perf_counter() - began
            deadline = time.perf_counter() + 1
            while beep.call_count < 2 and time.perf_counter() < deadline:
                time.sleep(0.01)
        return [c.args for c in beep.call_args_list], returned_after

    def test_start_rises_stop_falls(self):
        tones, _ = self.play_and_collect(True)
        self.assertEqual(tones, list(sounds.START))
        self.assertLess(tones[0][0], tones[1][0])
        tones, _ = self.play_and_collect(False)
        self.assertEqual(tones, list(sounds.STOP))
        self.assertGreater(tones[0][0], tones[1][0])

    def test_play_does_not_wait_for_the_beep(self):
        _, returned_after = self.play_and_collect(True)
        self.assertLess(returned_after, 0.05)

    def test_missing_sound_device_is_ignored(self):
        with mock.patch("sounds.winsound.Beep", side_effect=RuntimeError("no device")):
            sounds._beep(sounds.START)  # must not raise


if __name__ == "__main__":
    unittest.main()
