"""CreatorOS plugin launcher.

Claude starts this file with Python. It then runs the CreatorOS server with `uv`, using the exact
dependency versions pinned in uv.lock (`--locked`), so every install gets the same, reviewed packages.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def find_uv():
    found = shutil.which("uv")
    if found:
        return found
    home = Path.home()
    for c in (home / ".local" / "bin" / "uv", home / ".local" / "bin" / "uv.exe",
              home / ".cargo" / "bin" / "uv", home / ".cargo" / "bin" / "uv.exe"):
        if c.exists():
            return str(c)
    return None


def main() -> int:
    uv = find_uv()
    if not uv:
        sys.stderr.write(
            "CreatorOS needs 'uv' (Python package runner) and could not find it.\n"
            "Install it once, then restart Claude:\n"
            "  Windows (PowerShell): powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"\n"
            "  macOS/Linux:          curl -LsSf https://astral.sh/uv/install.sh | sh\n")
        return 1
    cmd = [uv, "run", "--locked", "--quiet", "--project", str(ROOT), str(ROOT / "main.py")]
    # Inherit stdin/stdout so the MCP protocol flows straight through; works the same on Windows.
    return subprocess.run(cmd, env=os.environ.copy()).returncode


if __name__ == "__main__":
    sys.exit(main())
