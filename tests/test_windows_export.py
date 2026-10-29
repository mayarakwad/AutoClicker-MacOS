"""Checks the Windows-only export (tools/export_windows.py) stays in step with the project."""
import ast
import tempfile
import unittest
from pathlib import Path

from tools import export_windows

ROOT = export_windows.ROOT


def imported_names(path, module):
    """Names imported from `module` in a Python file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {alias.name for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == module for alias in node.names}


class WindowsExportTest(unittest.TestCase):
    def test_windows_platforms_init_imports_the_same_names(self):
        main = imported_names(ROOT / "platforms" / "__init__.py", "platforms.windows")
        copy = imported_names(ROOT / "windows" / "platforms" / "__init__.py", "platforms.windows")
        self.assertEqual(copy, main)

    def test_left_out_files_still_exist(self):
        # A renamed Mac-only file would otherwise slip into the Windows copy.
        self.assertEqual([p for p in export_windows.LEFT_OUT if not (ROOT / p).exists()], [])

    def test_export_contents(self):
        files = export_windows.exported_files()
        self.assertFalse(export_windows.LEFT_OUT & set(files))
        self.assertFalse([name for name in files if name.startswith("windows/")])
        for name in ("main.py", "platforms/windows.py", "build.bat", ".github/workflows/build-windows.yml",
                     ".github/annotate_test_failures.py", "assets/app.ico", "build_installer.bat",
                     "installer/AutoClicker.iss", "installer/pin_taskbar.ps1", ".github/test_installer.ps1"):
            self.assertIn(name, files)
        self.assertIn(b"AutoClicker for Windows", files["README.md"])
        self.assertIn(b"This repository is generated", files["CLAUDE.md"])
        self.assertNotIn(b"darwin", files["platforms/__init__.py"])
        self.assertNotIn(b"darwin", files["requirements.txt"])
        self.assertIn(b"pynput", files["requirements.txt"])

    def test_refuses_to_export_into_the_project(self):
        with self.assertRaises(ValueError):
            export_windows.export(ROOT / "dist")

    def test_export_writes_files(self):
        with tempfile.TemporaryDirectory() as target:
            count = export_windows.export(target)
            self.assertEqual(count, len(list(p for p in Path(target).rglob("*") if p.is_file())))


if __name__ == "__main__":
    unittest.main()
