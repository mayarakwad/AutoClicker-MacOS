"""Writes the Windows-only copy of this project (github.com/mayarakwad/AutoClicker-Windows).

It takes the last commit (not uncommitted edits), leaves out the macOS-only
files, and lays windows/ on top: the Windows README and CLAUDE.md, the
Windows-only platforms/__init__.py and the Windows build workflow.

    .venv\\Scripts\\python tools\\export_windows.py C:\\Projects\\AutoClicker-Windows

Files the target's git tracks but the export no longer has are deleted;
untracked files there (.venv, build output) are left alone. Review, commit
and push in the target afterwards.
"""
import io
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
OVERLAY = "windows/"
LEFT_OUT = {
    "platforms/macos.py", "platforms/macos_keys.py", "build_mac.sh", ".github/workflows/build-mac.yml",
    "assets/app.icns", "assets/app.png",
    "tests/test_macos_backend.py", "tests/test_macos_keys.py", "tests/test_platform_macos.py",
    "tools/__init__.py", "tools/export_windows.py", "tests/test_windows_export.py",
}


def git(*args, cwd=ROOT):
    exe = shutil.which("git") or r"C:\Program Files\Git\cmd\git.exe"
    return subprocess.run([exe, *args], cwd=cwd, capture_output=True, check=True).stdout


def exported_files():
    """{path in the copy: contents} from the last commit."""
    files, overlay = {}, {}
    with tarfile.open(fileobj=io.BytesIO(git("archive", "--format=tar", "HEAD"))) as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            data = tar.extractfile(member).read()
            if member.name.startswith(OVERLAY):
                overlay[member.name[len(OVERLAY):]] = data
            elif member.name not in LEFT_OUT:
                files[member.name] = data
    files.update(overlay)
    requirements = files["requirements.txt"].splitlines(keepends=True)
    files["requirements.txt"] = b"".join(line for line in requirements if b'sys_platform == "darwin"' not in line)
    return files


def export(target):
    target = Path(target).resolve()
    if target == ROOT or ROOT in target.parents:
        raise ValueError("The target must be outside this project.")
    files = exported_files()
    if (target / ".git").exists():
        for old in git("ls-files", "-z", cwd=target).decode().split("\0"):
            if old and old not in files:
                (target / old).unlink(missing_ok=True)
    for name, data in files.items():
        path = target / PurePosixPath(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return len(files)


if __name__ == "__main__":
    destination = sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / "AutoClicker-Windows"
    print(f"Exported {export(destination)} files to {Path(destination).resolve()}")
