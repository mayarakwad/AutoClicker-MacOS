"""Start/stop beeps, played on a background thread so the UI never waits."""
import threading
import winsound

START = ((660, 60), (990, 80))  # rising: (Hz, ms)
STOP = ((990, 60), (660, 80))   # falling


def play(started):
    tones = START if started else STOP
    threading.Thread(target=_beep, args=(tones,), daemon=True).start()


def _beep(tones):
    try:
        for hz, ms in tones:
            winsound.Beep(hz, ms)
    except RuntimeError:
        pass  # no sound device
