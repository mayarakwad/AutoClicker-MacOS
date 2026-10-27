# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Windows desktop auto clicker modeled on OP Auto Clicker. Python 3.12 + tkinter (UI) + pynput (mouse control, global hotkeys), packaged later with PyInstaller.

Built in phases; the user tests each phase before the next one starts and says "commit this phase" when it works. Don't commit until they do, and stop after each phase.

1. Core engine, basic UI, F6 toggle (done)
2. Random offset ± N ms (default 40), double click, Pick location (click anywhere to capture X/Y), repeat N times vs until stopped
3. Hotkey setting dialog; settings saved as JSON in `%APPDATA%` and restored on launch
4. Record & Playback: record clicks with positions and delays, play once or loop
5. `build.bat` → single `dist\AutoClicker.exe` via PyInstaller `--onefile --windowed`

Requirements that apply to every phase: clicking never blocks the UI; Esc or the mouse in the top-left corner stops clicking immediately; inputs are validated (no empty/negative values, interval ≥ 1 ms); the status line shows Running/Stopped and the click count.

## Commands

Python and Git were installed mid-session and may not be on PATH yet. Use the venv interpreter directly, and `C:\Program Files\Git\cmd\git.exe` if `git` isn't found.

```
.venv\Scripts\python main.py                      # run the app
.venv\Scripts\python -m unittest                  # all tests
.venv\Scripts\python -m unittest tests.test_engine.ClickEngineTest.test_failsafe_corner_stops_clicking
.venv\Scripts\pip install -r requirements.txt     # deps (pinned)
```

## Architecture

Three threads; only the main thread touches tkinter:

- **Main thread (`ui.App`)**: owns the Tk window. A `root.after` loop every 50 ms (`_poll`) drains `App.events` (a `queue.Queue`) and refreshes buttons and the status line from the engine's state. Engine state is polled, never pushed via callbacks.
- **Hotkey thread (`hotkeys.HotkeyListener`)**: a pynput keyboard listener. It only observes keys, never suppresses them, so Esc and F6 still reach other apps. Callbacks just put `"toggle"` / `"escape"` on the queue, and held-key auto-repeat is ignored. `key_name()` gives the string form used for hotkey names (`"f6"`).
- **Click thread (`engine.ClickEngine`)**: has no UI imports. The UI calls `start(ClickConfig)` / `stop(reason)` and reads `running`, `clicks` and `stop_reason`. The top-left-corner fail-safe lives in the engine loop; Esc is handled by the UI as `stop("Esc pressed")`.

Engine timing details that are easy to break:
- Clicks are scheduled against `perf_counter` deadlines (no drift, no catch-up bursts).
- Waiting uses `time.sleep` in slices of at most 50 ms, so stop and the fail-safe react quickly even with long intervals. `time.sleep` uses a high-resolution timer on Python 3.11+ on Windows. Don't replace it with `Event.wait`, which falls back to about 15.6 ms granularity, especially while the window is minimized.

`main.enable_dpi_awareness()` must run before the Tk root is created. pynput does not set DPI awareness itself, and without it cursor coordinates are scaled wrongly on 125%/150% displays (this matters for Pick location and recording).

Tests inject a fake mouse via `ClickEngine(mouse=...)`, which must provide `position` and `click(button, count=1)`. Tests must never send real input.
