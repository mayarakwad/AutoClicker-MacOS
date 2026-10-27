# AutoClicker

A lightweight Windows auto clicker modeled on OP Auto Clicker.
Python 3.12, tkinter for the window, pynput for mouse control and global hotkeys.

**Progress:** Phase 2 of 5 (core clicking, F6, fail-safe, random offset, double click, pick location, repeat count).

## Run from source

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pythonw main.py
```

Use `python` instead of `pythonw` to keep a console window open for error messages.

## How to use

- **Click interval:** hours, mins, secs and milliseconds (at least 1 ms in total). Tick **Random offset ± N ms** to vary each delay randomly by up to N ms; a delay never drops below 1 ms.
- **Click options:** mouse button (Left/Right/Middle) and click type (Single/Double). A double click counts as one click in the status line.
- **Click repeat:** stop after N clicks, or repeat until stopped.
- **Cursor position:**
  - **Current location** clicks wherever the cursor is.
  - **Pick location** clicks at X/Y. Press the **Pick location** button, then click anywhere on screen. That click is captured, not passed to the app underneath. Press Esc to cancel.
  - With a picked location, the cursor jumps to X/Y for each click and straight back, so you can still move the mouse.
  - X/Y can be negative on screens left of or above the main one.
- Press **Start** or **F6**. Press **Stop** or **F6** again to stop. F6 works even when the window is minimized or another app has focus.
- **Fail-safe:** press **Esc**, or move the mouse into the top-left corner of the main screen, and clicking stops immediately.
- The status line shows Running/Stopped, the click count, and why clicking stopped.

Test stopping (F6, Esc, the corner) with a slow interval before trying very short ones.

## Tests

```
.venv\Scripts\python -m unittest
```

The tests use a fake mouse and send no real input.

## Files

| File | What it does |
|---|---|
| `main.py` | Entry point. Turns on DPI awareness, then opens the window. |
| `ui.py` | tkinter window. Validates input and starts/stops the engine. |
| `engine.py` | Click loop on a background thread. No UI code. |
| `mouse_io.py` | Clicking (pynput, plus one SendInput batch for clicks at X/Y), Pick location capture, on-screen check. |
| `hotkeys.py` | Global F6 / Esc listener (pynput). |
| `tests/` | Unit tests. |
