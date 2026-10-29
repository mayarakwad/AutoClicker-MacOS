# AutoClicker

A lightweight auto clicker for Windows and macOS, modeled on OP Auto Clicker.
Python 3.12 and tkinter, with pynput (Windows) or Quartz (macOS) for mouse control and global hotkeys.

**Progress:** all 5 phases built for Windows (features plus `build.bat` packaging), plus personalization. The macOS version is written and builds on GitHub Actions, but **hasn't been tested on a real Mac yet**; see [macOS](#macos).

## Build the .exe

```
build.bat
```

This creates the virtual environment if needed, installs `requirements.txt`, and builds `dist\AutoClicker.exe`, a single file of about 11 MB with no console window, using PyInstaller `--onefile --windowed`. The exe has the app icon and version details (Properties > Details). Settings still live in `%APPDATA%\AutoClicker\settings.json`.

The exe isn't code-signed, which matters in two cases:

- **SmartScreen:** on another PC, a downloaded copy shows a SmartScreen warning the first time. Click **More info**, then **Run anyway**.
- **Smart App Control:** Windows 11's Smart App Control blocks unsigned programs outright, with no "Run anyway". The error is "An Application Control policy has blocked this file". On a PC with it turned on, run `make_shortcut.bat` instead. It puts an **AutoClicker** shortcut on the Desktop that runs the app from source through the venv's `pythonw.exe`, which is signed by the Python Software Foundation and so is allowed. It has the same icon and no console window. The other option is to sign the exe with a certificate from a trusted certificate authority.

To change the icon, edit and run `.venv\Scripts\python assets\make_icon.py` (it writes the Windows and macOS icons), then rebuild.

## Run from source

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pythonw main.py
```

Use `python` instead of `pythonw` to keep a console window open for error messages.

## How to use

- **Click interval:** hours, mins, secs, milliseconds and nanoseconds, at least 0.1 ms (100000 ns) in total. For example, 1 ms + 500000 ns = 1.5 ms. Tick **Random offset ± N ms** to vary each delay randomly by up to N ms; a delay never drops below 0.1 ms.
  - Intervals under 2 ms are timed by watching the clock instead of sleeping, so one CPU core stays busy while clicking that fast.
  - The operating system limits how fast clicks actually go through. On the development PC that was about 3,500 clicks a second at the cursor and 1,500 at a picked location. Shorter intervals just click that fast, and many apps and games don't register clicks that quickly.
- **Click options:** mouse button (Left/Right/Middle) and click type (Single/Double). A double click counts as one click in the status line.
- **Click repeat:** stop after N clicks, or repeat until stopped.
- **Cursor position:**
  - **Current location** clicks wherever the cursor is.
  - **Pick location** clicks at X/Y. Press the **Pick location** button, then click anywhere on screen. That click is captured, not passed to the app underneath. Press Esc to cancel.
  - With a picked location, the cursor jumps to X/Y for each click and straight back, so you can still move the mouse.
  - X/Y can be negative on screens left of or above the main one.
- Press **Start** or **F6**. Press **Stop** or **F6** again to stop. F6 works even when the window is minimized or another app has focus.
- **Hotkey setting:** change F6 to another key or combination (for example F8 or Ctrl+Shift+S).
  - Click **Change**, press the new key, then **OK**. **Default (F6)** puts it back.
  - Esc is reserved for the fail-safe.
  - Letters, digits, Space and Enter need Ctrl or Alt. Keys still reach other apps, so a plain letter would start clicking while you type.
- **Record & Playback:** opens a window for recording a sequence of clicks and playing it back.
  - **Recording:** click **Record**, then click anywhere on screen. Each click's button, position and delay since the previous click is listed. The first delay counts from pressing Record. Clicks on AutoClicker's own windows aren't recorded, and the window stays on top while recording so **Stop** is always reachable. F6 or Esc also stops recording.
  - **Playback:** choose **Once** or **Loop until stopped**, then press **Play** or F6. The step being played is highlighted. F6, Esc or the top-left corner stops it. Like Pick location, the cursor jumps to each point and straight back.
  - While this window is open, F6 controls playback instead of the normal clicker.
  - The last recording is saved with your settings.
- **Personalize:** changes preview as you make them. **OK** keeps them, **Cancel** undoes them, and **Defaults** resets this dialog's options.
  - **Theme:** Same as Windows (follows Windows' light/dark app mode, even while AutoClicker is open), Light, or Dark. Dark covers every window, drop-down lists and title bars.
  - **Always on top:** keeps the main window above other apps.
  - **Opacity:** makes the main window see-through, from 40% to 100%.
  - **Sounds:** a rising beep when clicking starts and a falling one when it stops, whatever stopped it. **Test** plays it.
  - **Window position:** the window always reopens where you left it, as long as that spot is still on a screen.
- **Fail-safe:** press **Esc**, or move the mouse into the top-left corner of the main screen, and clicking stops immediately.
- The status line shows Running/Stopped, the click count, and why clicking stopped.
- **Saved settings:** all fields, the hotkey, the last recording, personalization and the window position are saved to `settings.json` (in `%APPDATA%\AutoClicker` on Windows, `~/Library/Application Support/AutoClicker` on macOS) and restored on the next launch. Saving happens when you press Start, change the hotkey, press OK in Personalize, close the Record & Playback window, or close the app. Delete that file to go back to defaults. Missing or invalid values fall back to defaults.

Test stopping (F6, Esc, the corner) with a slow interval before trying very short ones.

## Tests

```
.venv\Scripts\python -m unittest
```

The tests use a fake mouse and send no real input. The macOS backend is also tested on Windows, against a fake Quartz (`tests/test_macos_backend.py`).

## macOS

The Mac version shares all of the app's code except `platforms/macos.py`, which uses Quartz (through pyobjc) instead of pynput and Win32.

**Not yet tested on a real Mac.** On GitHub's Macs the tests pass, the app builds, and it starts without errors. Real clicking, hotkeys and permissions can only be tried by a person on a Mac, so expect a round of fixes after the first real test.

### Install

On an Apple Silicon Mac (M1 or later), download **[AutoClicker-Setup.pkg](https://github.com/mayarakwad/AutoClicker-MacOS/releases/latest/download/AutoClicker-Setup.pkg)** from the latest release and open it. The installer asks:

- **Where to install.** Under **Change Install Location**: **Install for all users of this computer** puts it in `/Applications` and needs an admin password. **Install for me only** puts it in `~/Applications` and doesn't. You can also pick another disk. (macOS's installer can't install into any other folder.)
- **Extras.** Under **Customize**, **Add to Dock** and **Desktop link** are ticked; untick the ones you don't want. Both are for the user who runs the installer, even when installing for all users.

If macOS says it can't verify the developer, go to **System Settings > Privacy & Security** and click **Open Anyway**. Then allow AutoClicker under Accessibility and Input Monitoring (see [Permissions](#permissions)).

To update, run the newer installer. To uninstall, drag AutoClicker from Applications to the Trash, then drag it off the Dock and delete the Desktop link.

The installer also works from Terminal, which skips the "can't verify the developer" step. For all users:

```
curl -fL -o /tmp/AutoClicker-Setup.pkg https://github.com/mayarakwad/AutoClicker-MacOS/releases/latest/download/AutoClicker-Setup.pkg && sudo installer -pkg /tmp/AutoClicker-Setup.pkg -target /
```

For just you, use `installer -pkg /tmp/AutoClicker-Setup.pkg -target CurrentUserHomeDirectory` (no `sudo`). Both add the Dock item and Desktop link.

### Install with one command

Without the installer, paste this into Terminal. It downloads the latest release, unpacks it into `~/Applications` and opens it:

```
mkdir -p ~/Applications && curl -fL -o /tmp/AutoClicker-mac.zip https://github.com/mayarakwad/AutoClicker-MacOS/releases/latest/download/AutoClicker-mac.zip && ditto -x -k /tmp/AutoClicker-mac.zip ~/Applications && open ~/Applications/AutoClicker.app
```

Then allow it under Accessibility and Input Monitoring (see [Permissions](#permissions)).

Releases are published by the GitHub build when a version tag is pushed: `git tag v1.0.2` then `git push origin v1.0.2`. Or, on GitHub, open **Actions > macOS build > Run workflow** and enter the tag. Either way, the tag must match the version in `version_info.txt`.

### Run from source

Install Python 3.12 from [python.org](https://www.python.org/downloads/macos/). Apple's built-in `python3` comes with an old Tk without dark-mode support. Then, in Terminal:

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

### Permissions

macOS only lets an app click and watch the keyboard after you allow it, under **System Settings > Privacy & Security**:

- **Accessibility:** for clicking and Pick location.
- **Input Monitoring:** for the F6 hotkey, Esc and recording.

AutoClicker asks on first launch. Until both are allowed, its status line says what's missing and Start won't run. Allow **Terminal** (or whichever app you started it from) when running from source, and **AutoClicker** for the built app. The hotkey starts working within a couple of seconds of allowing it, with no restart needed.

### Build the app

On a Mac:

```
bash build_mac.sh
```

This creates `dist/AutoClicker.app` and `dist/AutoClicker-mac.zip` for sharing. It's built for the Mac's own chip, which is Apple Silicon on the GitHub runner. The app's version comes from `version_info.txt`.

To build the installer as well:

```
bash build_mac_installer.sh
```

This creates `dist/AutoClicker-Setup.pkg` from the app and `mac_installer/`, using macOS's own `pkgbuild` and `productbuild`.

Without a Mac, push this project to GitHub. `.github/workflows/build-mac.yml` then builds the app and the installer on a GitHub-hosted Mac, runs the tests, checks the app starts, and installs the installer for one user and for all users. Download **AutoClicker-mac** (the zip and the installer) from the run's **Artifacts**.

The app and installer aren't signed with an Apple Developer ID, which has two effects:

- **First launch:** on a Mac that downloaded it, macOS says it can't verify the developer. Open **System Settings > Privacy & Security** and click **Open Anyway**.
- **After rebuilding:** each build is a new app as far as macOS is concerned, so you may need to allow Accessibility and Input Monitoring again.

### Mac differences

- **F6:** most Mac keyboards need **Fn+F6**, unless "Use F1, F2, etc. keys as standard function keys" is on. Hotkey setting can pick something else, such as Cmd+Shift+S.
- **Modifiers:** hotkeys can use **Cmd**, and Alt is shown as **Option**.
- **Fail-safe corner:** the top-left corner of the main display, next to the Apple menu.
- **Theme:** uses the native Mac look in both light and dark. "Same as macOS" follows System Settings > Appearance.
- **Password fields:** while one is focused, macOS hides keystrokes from other apps, so the hotkey doesn't work there.

## Files

| File | What it does |
|---|---|
| `main.py` | Entry point. Prepares the process (DPI awareness on Windows), then opens the window. |
| `ui.py` | tkinter window. Validates input and starts/stops the engine. |
| `engine.py` | Clicking and playback on a background thread. No UI code. |
| `recorder.py` | Records clicks anywhere on screen; converts recordings to and from JSON. |
| `recorder_window.py` | Record & Playback window. |
| `platforms/` | Everything OS-specific: `windows.py` (pynput + Win32) and `macos.py` (Quartz), with the same names. Clicking, Pick location, recording, key events, screens, sounds, settings folder, title bars. |
| `hotkeys.py` | Global start/stop hotkey and Esc logic, key combos and their display names. |
| `hotkey_dialog.py` | Hotkey setting dialog. |
| `settings.py` | Reads and writes the settings JSON file. |
| `personalize_dialog.py` | Personalize dialog. |
| `theme.py` | Light/dark styling for every window, including title bars. |
| `tests/` | Unit tests. |
| `build.bat` | Builds `dist\AutoClicker.exe`. |
| `build_mac.sh` | Builds `dist/AutoClicker.app` (run on a Mac). |
| `build_mac_installer.sh`, `mac_installer/` | Builds the Mac installer, `dist/AutoClicker-Setup.pkg` (run on a Mac). |
| `.github/workflows/build-mac.yml` | Builds and tests the Mac app on GitHub Actions. |
| `make_shortcut.bat` | Creates a Desktop shortcut that runs the app from source (for PCs with Smart App Control on). |
| `version_info.txt` | Version details embedded in the exe. |
| `assets/` | `app.ico` (Windows), `app.icns` and `app.png` (macOS), and the script that draws them. |
