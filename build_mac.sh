#!/bin/bash
# Builds dist/AutoClicker.app and dist/AutoClicker-mac.zip. Run on a Mac:
#   bash build_mac.sh
# Uses python3 from python.org (its Tk supports dark mode); set PYTHON to use another.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "Creating virtual environment..."
    "${PYTHON:-python3}" -m venv .venv
fi
if ! .venv/bin/python -c "import tkinter" 2>/dev/null; then
    echo "This Python has no Tk. Install Python 3.12 from python.org, delete .venv and run again."
    exit 1
fi

echo "Installing requirements..."
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt

echo "Building..."
.venv/bin/python -m PyInstaller --noconfirm --clean --log-level WARN \
    --windowed --name AutoClicker --osx-bundle-identifier com.autoclicker.app \
    --icon assets/app.icns --add-data "assets/app.png:assets" \
    --exclude-module platforms.windows \
    main.py

rm -f dist/AutoClicker-mac.zip
ditto -c -k --keepParent dist/AutoClicker.app dist/AutoClicker-mac.zip  # keeps the app's symlinks and permissions

echo
echo "Done: dist/AutoClicker.app (to share: dist/AutoClicker-mac.zip)"
