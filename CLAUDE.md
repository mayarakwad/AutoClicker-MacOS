# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Desktop auto clicker for Windows and macOS, modeled on OP Auto Clicker. Python 3.12 + tkinter (UI). Mouse control and global hotkeys come from pynput + Win32 on Windows and Quartz (pyobjc) on macOS. Packaged with PyInstaller.

Built in phases; the user tests each phase before the next one starts and says "commit this phase" when it works. Don't commit until they do, and stop after each phase.

1. Core engine, basic UI, F6 toggle (done)
2. Random offset ± N ms (default 40), double click, Pick location (click anywhere to capture X/Y), repeat N times vs until stopped (done)
3. Hotkey setting dialog; settings saved as JSON in `%APPDATA%` and restored on launch (done)
4. Record & Playback: record clicks with positions and delays, play once or loop (done)
5. `build.bat` → single `dist\AutoClicker.exe` via PyInstaller `--onefile --windowed` (built; see Packaging)
6. Personalize dialog: theme (system/light/dark), always on top, opacity, start/stop sounds; window position remembered (built)
7. macOS version (built, **not yet run on a real Mac**; the user will test on a borrowed or rented Mac):
   - M1: OS-specific code moved into `platforms/` (verified on Windows).
   - M2: `platforms/macos.py` (tested only against a fake Quartz).
   - M3: `build_mac.sh` plus the GitHub Actions build.
   - The user has no Mac. Expect the first real-Mac test to need fixes.
   - GitHub repo: https://github.com/mayarakwad/AutoClicker (public). Its macOS build passes: tests (including the real Quartz checks), build, and a 10 s launch check.
   - Clicking, hotkeys and permissions can't be tested there, because nobody can grant TCC permissions on GitHub's machines.
   - Logs need sign-in, but `.github/annotate_test_failures.py` posts failing tests as annotations, readable without sign-in via `api.github.com/repos/mayarakwad/AutoClicker/check-runs/<job id>/annotations`.
   - Commit messages: on Windows PowerShell 5.1, pass them with `git commit -F <file>`. Double quotes inside `-m` get mangled.
   - Releases: pushing a `v*` tag makes the workflow's last step run `gh release create` with `dist/AutoClicker-mac.zip`. The job has `contents: write` for that.
   - The one-command install (README) downloads `releases/latest/download/AutoClicker-mac.zip`. curl doesn't set the quarantine flag, so Gatekeeper's "Open Anyway" isn't needed.
   - The app is arm64 only, so it won't run on Intel Macs.

Requirements that apply to every phase: clicking never blocks the UI; Esc or the mouse in the top-left corner stops clicking immediately; inputs are validated (no empty/negative values, interval ≥ 1 ms); the status line shows Running/Stopped and the click count.

## Commands

Python and Git were installed mid-session and may not be on PATH yet. Use the venv interpreter directly, and `C:\Program Files\Git\cmd\git.exe` if `git` isn't found.

```
.venv\Scripts\python main.py                      # run the app
.venv\Scripts\python -m unittest                  # all tests
.venv\Scripts\python -m unittest tests.test_engine.ClickEngineTest.test_failsafe_corner_stops_clicking
.venv\Scripts\pip install -r requirements.txt     # deps (pinned)
cmd /c C:\Projects\AutoClicker\build.bat          # -> dist\AutoClicker.exe (from PowerShell, pass the full path)
.venv\Scripts\python assets\make_icon.py          # regenerate assets\app.ico
cmd /c C:\Projects\AutoClicker\make_shortcut.bat  # Desktop shortcut: venv pythonw.exe + main.py + app icon
```

On a Mac: `.venv/bin/python main.py` to run, `bash build_mac.sh` to build `dist/AutoClicker.app` and `dist/AutoClicker-mac.zip`. Pushing to GitHub runs `.github/workflows/build-mac.yml` (macos-latest: unit tests, build, upload the zip, check the app starts).

## Packaging

- PyInstaller's contrib hook (`hook-pynput`) already collects pynput's backend submodules, so no `--hidden-import` is needed.
- `assets\app.ico` is bundled with `--add-data` and found at runtime through `main.ASSETS`, which uses `sys._MEIPASS` when frozen. `root.iconbitmap(default=...)` applies the icon to dialogs too.
- `assets\make_icon.py` draws the icon in pure Python (no Pillow), using all-BMP ICO entries so both Tk and Windows read every size.
- **Smart App Control is ON on this dev PC.** It blocks the unsigned exe from running (WinError 4551; Code Integrity events 3077/3033).
  - Don't try to bypass it, and don't change security settings.
  - The exe has been built and its contents checked with `python -m PyInstaller.utils.cliutils.archive_viewer -l -r`, but it has not been run here.
  - `.venv\Scripts\pythonw.exe` is PSF-signed and allowed, so running from source works.
  - The user runs the app through the Desktop shortcut from `make_shortcut.bat` (OneDrive Desktop).
  - The venv's `pythonw.exe` is a launcher that starts the base install's `pythonw.exe`, which is also PSF-signed. So the app's window belongs to the base `pythonw.exe` process, not the venv one.
- To test a frozen build end to end, launch it with `APPDATA` pointed at a temp folder, so it never touches the user's real settings.
- `build.bat` passes `--exclude-module platforms.macos` and `build_mac.sh` passes `--exclude-module platforms.windows`. PyInstaller follows both branches of `platforms/__init__.py`.
- macOS app:
  - It's a `--windowed` onedir `.app` (PyInstaller deprecates onefile `.app`s) with `assets/app.icns`, and `assets/app.png` bundled for `iconphoto`.
  - It's ad-hoc signed, not with a Developer ID. So Gatekeeper's "Open Anyway" is needed on other Macs, and TCC permissions may need re-granting after each rebuild.
  - `ditto` makes the zip, because GitHub's artifact upload alone would drop the app's symlinks and permissions.
  - It's built for the build machine's chip only (arm64 on the GitHub runner).
- `assets/make_icon.py` writes `app.ico`, `app.png` and `app.icns` (PNG entries, written directly, so no `iconutil` is needed).

## Architecture

OS layer: everything OS-specific lives in `platforms/windows.py` and `platforms/macos.py`, which define the same names. `platforms/__init__.py` imports one of them by `sys.platform`, and the rest of the app imports only from `platforms`.
- The names are: `Mouse`, `PointPicker`, `MouseListener`, `KeySource`, `on_screen`, `is_own_window`, `play_sound`, `settings_folder`, `system_uses_dark`, `set_window_dark`, `permission_problem`, `request_permissions`, `prepare_process`, `set_app_icon`, `set_clicking`, plus the constants (`KEY_NAMES`, `MODIFIER_LABELS`, `TYPING_MODIFIERS`, `EXAMPLE_COMBO`, `OS_NAME`, `NATIVE_THEME`, `NATIVE_DARK`).
- Add a new OS-specific function to both backends and to the import lists in `__init__.py`. `tests/test_macos_backend.py` checks the Mac module defines everything the package imports.
- Buttons are passed around as names (`"left"`, `"right"`, `"middle"`). Keys are OS-independent names (`"f6"`, `"a"`, `"page_up"`); `"win"` is the Windows key on Windows and Command on macOS.

Several threads; only the main thread touches tkinter:

- **Main thread (`ui.App`)**: owns the Tk window. A `root.after` loop every 50 ms (`_poll`) drains `App.events` and refreshes buttons and the status line from the engine's state. Engine state is polled, never pushed via callbacks.
  - `App.events` is a `queue.Queue` of tuples: `("toggle",)`, `("escape",)`, `("picked", x, y)`, `("recorded", combo)` (hotkey dialog), `("step", Step)` (click recorder).
  - Esc always stops a running engine first (fail-safe priority, which also covers playback), then also cancels a pick, a hotkey recording or a click recording.
  - While the Record & Playback window is open, `"toggle"` goes to `RecorderWindow.toggle()` (play/stop) instead of the normal clicker, and `_poll` calls its `refresh()`.
  - `close()` cancels the pending `after` jobs.
- **Hotkey thread (`platforms.KeySource`, driven by `hotkeys.HotkeyListener`)**: it only observes keys, never suppresses them, so Esc and the hotkey still reach other apps. `KeySource` calls `on_press(name, modifiers)` / `on_release(name)`. `HotkeyListener` holds the OS-independent logic: it only queues events and ignores held-key auto-repeat.
  - On Windows it's a pynput keyboard listener. Keys are named from the virtual-key code (`vk_name`), never pynput's `char`, because Ctrl+A reports char `'\x01'`. Left and right modifiers share one name.
  - On macOS it's a listen-only Quartz event tap. Keys are named from key codes via `platforms/macos_keys.py` (pure Python, tested on any OS; ANSI positions, so letters follow physical position, not layout), and modifiers come from the event's flags. pynput isn't used on macOS because its keyboard listener crashes on recent macOS.
  - A hotkey is a canonical combo string: modifiers in `MODIFIER_ORDER`, then the key (`"ctrl+shift+f6"`). The press must match the modifiers exactly.
  - On Windows, modifiers come from `GetAsyncKeyState` at press time (`held_modifiers`), not tracked key-ups, so a missed release can't leave Ctrl stuck.
  - `combo_problem()` rejects Esc (fail-safe) and typing keys without one of `platforms.TYPING_MODIFIERS` (Ctrl/Alt on Windows; Cmd/Ctrl/Option on macOS).
  - `record(cb)` makes the next non-modifier press go to `cb` instead of toggling. The Hotkey setting dialog (`hotkey_dialog.HotkeyDialog`) records through this global listener, not Tk key events, so a recorded name is exactly what the listener matches. App forwards `("recorded", combo)` to `dialog.key_pressed`.
- **Pick hook thread (`platforms.PointPicker`)**: exists only while picking. It captures the next left button down, swallows the down/up pair system-wide, then stops itself. On Windows that's a pynput `win32_event_filter` with `suppress_event()`; on macOS it's an active Quartz event tap returning `None`. While picking, the main window is withdrawn, a cursor-following tooltip shows X/Y, F6 is ignored and Esc cancels.
- **Click recorder thread (`recorder.ClickRecorder` on `platforms.MouseListener`)**: exists only while recording. It turns each left/right/middle press into a `Step(delay_ms, button, x, y)`, with the delay measured since the previous press (or since `start()`).
  - It doesn't suppress clicks.
  - It skips presses on this process's own windows (`platforms.is_own_window` compares the PID of the window under the point).
  - `RecorderWindow` (modal) makes itself topmost while recording, so its Stop button is reachable without a taskbar click that would get recorded.
- **Click thread (`engine.ClickEngine`)**: has no UI imports. The UI calls `start(config)` / `stop(reason)` and reads `running`, `clicks` and `stop_reason`.
  - `start(ClickConfig)` runs `_run`, interval clicking. `clicks` counts actions, so a double click counts once, and `repeat` compares against it.
  - `start(PlaybackConfig(steps, loop))` runs `_play`. Each step waits its `delay_ms` (deadline-based) then calls `click_at`, so playback returns the cursor too. The recorder window uses the App's single engine, so the main status line shows playback as Running.
  - The top-left-corner fail-safe lives in `_wait_until`, shared by both run kinds. Esc is handled by the UI as `stop("Esc pressed")`.

`platforms.Mouse` is the engine's output:
- `click()` clicks at the cursor. On Windows it uses pynput.
- `click_at(x, y)` moves to X/Y, clicks (down/up, ×2 for double), then moves back to where the cursor was.
  - On Windows it's one SendInput batch. Keep it one batch: separate SetCursorPos + SendInput calls race, and the click can land after the cursor is restored. Moving the physical mouse at that exact instant can still nudge a click a few pixels; this was seen in testing while the user was moving the mouse.
  - On macOS it's a run of `CGEventPost` mouse events, which stay in order. The click state field 1, 2 makes a double click.
- Restoring the cursor is deliberate: if the cursor stayed parked at X/Y, the corner fail-safe would be unreachable at short intervals.
- `normalize()` rounds up because Windows maps absolute coordinates back with `n * size // 65536`. This was verified pixel-exact on the user's 1920×1080 screen.

Settings are handled as follows:
- `settings.py` is dict in, dict out, written atomically to `%APPDATA%\AutoClicker\settings.json`. A missing or corrupt file gives `{}`.
- What counts as a valid value lives in the UI: `App._setting_vars()` maps each key to its Tk variable and a validity check. `_apply_settings` skips missing or invalid values, which keep their defaults.
- Settings are saved on Start, on hotkey OK, when the recorder window closes, and on app close.
- To add a setting backed by a Tk variable, add it to `_setting_vars`.
- The recording is not a Tk variable. It lives in `App.steps` / `App.playback_loop` and is stored as `"recording"` (via `recorder.dump_steps` / `load_steps`, which is all-or-nothing: any bad item gives `[]`) and `"playback_loop"`.
- `App(root, settings_path=...)` lets tests use a temp file. Tests must never write the real `%APPDATA%` file.

Personalization:
- `theme.apply(root, mode)` restyles every open window.
  - Light is the native `vista` theme. Dark is `clam` plus our colors.
  - It also recolors combobox drop-down lists (plain Tk Listboxes that ttk styles don't reach) and sets dark title bars (`DWMWA_USE_IMMERSIVE_DARK_MODE`).
- Every new `Toplevel` must call `theme.style_window(win)`, and status colors must come from `theme.color(...)`, never hard-coded hex, so they stay readable in dark mode.
- Dark checkboxes and the slider handle are image elements drawn by `_raster` and created once per run (ttk elements can't be redefined).
  - clam's own checkbox shows ✕ marks.
  - clam's slider shares its `background` with the track.
- `"system"` mode is re-checked every `SYSTEM_THEME_POLLS` polls (about 2 s) in `_poll`.
- `theme_mode`, `always_on_top`, `opacity` and `sounds` are App Tk variables in `_setting_vars`. `_follow_look` applies them and traces changes.
  - `PersonalizeDialog` edits those variables directly, so changes preview live. Cancel restores the values it saw on open.
  - Opacity applies to the main window only.
- `_refresh` detects running→stopped and stopped→running transitions, so every start and stop (any cause, including playback) can beep. `platforms.play_sound` runs `winsound.Beep` on a thread (Windows) or `afplay` with system sounds (macOS).
- On macOS the native `aqua` look has its own dark mode (`NATIVE_DARK`). `theme.apply` then skips the clam styling, background colors and dropdown recoloring, and `set_window_dark` sets each window's appearance through `::tk::unsupported::MacWindowStyle appearance`.
- The window position (`window_x`/`window_y`) is saved only while `root.state() == "normal"`, because minimized windows report -32000. It's restored only if a title-bar point is `on_screen`.

The UI enables the offset, repeat and X/Y entries through `trace_add` on their option variables, not widget `command=`, so values set in code (e.g. restored settings) update the entries too. X/Y allow a leading minus (screens left of or above the main one) and are checked with `on_screen()`. Every other number field accepts digits only.

Engine timing details that are easy to break:
- Clicks are scheduled against `perf_counter` deadlines (no drift, no catch-up bursts).
- Waiting uses `time.sleep` in slices of at most 50 ms, so stop and the fail-safe react quickly even with long intervals. `time.sleep` uses a high-resolution timer on Python 3.11+ on Windows. Don't replace it with `Event.wait`, which falls back to about 15.6 ms granularity, especially while the window is minimized.
- On macOS, App Nap throttles the timers of apps whose windows are hidden, which is exactly when an auto clicker runs.
  - `_refresh` calls `platforms.set_clicking(running)` on every start and stop. On macOS this holds an `NSProcessInfo` latency-critical activity while clicking; on Windows it does nothing.
  - GitHub's shared macOS runners oversleep by 10-80 ms per wait (16 instead of 25 clicks in 0.5 s at 20 ms; 0.37 s for a 0.12 s playback). With `CI=true`, the timing tests (`SHARED_CI` in `tests/test_engine.py`) only check for hangs and bursts; real machines get the precise limits.

`platforms.prepare_process()` must run before the Tk root is created. On Windows it turns on DPI awareness: pynput doesn't, and without it cursor coordinates are scaled wrongly on 125%/150% displays (this matters for Pick location and recording). On macOS it does nothing, because Quartz and Tk both use points with a top-left origin.

macOS permissions:
- Clicking needs Accessibility, and key/mouse event taps need Input Monitoring.
- `permission_problem()` returns a status-line message when either is missing. `App` shows it in place of the status, blocks Start, re-checks every `SYSTEM_THEME_POLLS`, and calls `request_permissions()` once at launch.
- `_EventTap` retries creating its tap every 2 s, so a hotkey starts working once permission is granted, without a restart.

Tests inject a fake mouse via `ClickEngine(mouse=...)`, which must provide `position`, `click(button, count=1)` and `click_at(x, y, button, count=1)`. Tests must never send real input.

Mac tests:
- `tests/test_macos_backend.py` imports `platforms/macos.py` against a fake `Quartz`/`HIServices`. The fake contains only the pyobjc names the backend may use, with real pyobjc 12 values, so a misspelled name fails on any OS.
- When adding a Quartz call, first check that the name exists in pyobjc's metadata, then add it to the fake.
- `tests/test_platform_macos.py` runs real Quartz checks, only on a Mac (CI).
