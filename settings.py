"""Settings file: %APPDATA%\\AutoClicker\\settings.json.

Plain dict in, plain dict out. The UI decides which values are valid, so a
missing, corrupt or hand-edited file just falls back to defaults.
"""
import json
import os
from pathlib import Path


def default_path():
    base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
    return Path(base) / "AutoClicker" / "settings.json"


def load(path=None):
    path = Path(path or default_path())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(data, path=None):
    """Write to a temp file and swap it in, so a crash can't leave half a file."""
    path = Path(path or default_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)
