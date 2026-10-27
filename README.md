# AutoClicker

A lightweight Windows auto clicker modeled on OP Auto Clicker.
Python 3.12, tkinter for the window, pynput for mouse control and global hotkeys.

**Progress:** Phase 1 of 5 (core engine, basic window, F6 start/stop, fail-safe).

## Run from source

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pythonw main.py
```

Use `python` instead of `pythonw` to keep a console window open for error messages.

## How to use

- Set the click interval (hours, mins, secs, milliseconds; at least 1 ms in total) and the mouse button.
- Press **Start** or **F6**. Press **Stop** or **F6** again to stop. F6 works even when the window is minimized or another app has focus.
- **Fail-safe:** press **Esc**, or move the mouse into the top-left corner of the main screen, and clicking stops immediately.
- The status line shows Running/Stopped, the click count, and why clicking stopped.

Clicks happen where the mouse cursor is. Test stopping (F6, Esc, the corner) with a slow interval before trying very short ones.

## Tests

```
.venv\Scripts\python -m unittest
```

The engine tests use a fake mouse, so nothing is actually clicked.

## Files

| File | What it does |
|---|---|
| `main.py` | Entry point. Turns on DPI awareness, then opens the window. |
| `ui.py` | tkinter window. Validates input and starts/stops the engine. |
| `engine.py` | Click loop on a background thread. No UI code. |
| `hotkeys.py` | Global F6 / Esc listener (pynput). |
| `tests/` | Engine unit tests. |
