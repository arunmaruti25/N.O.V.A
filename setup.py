"""Set up NOVA and its Python and frontend dependencies on Windows."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV = ROOT / "backend" / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print(f"\n> {' '.join(command)}")
    completed = subprocess.run(command, cwd=cwd)
    if completed.returncode:
        raise SystemExit(f"Command failed with exit code {completed.returncode}: {' '.join(command)}")


def find_python() -> str:
    for command in (("py", "-3.14"), ("python",)):
        executable = shutil.which(command[0])
        if not executable:
            continue
        try:
            result = subprocess.run(
                [executable, *command[1:], "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and tuple(map(int, result.stdout.strip().split("."))) >= (3, 14):
                return executable
        except (OSError, ValueError):
            pass
    return ""


def install_windows_prerequisite(package_id: str, display_name: str) -> None:
    if os.name != "nt" or not shutil.which("winget"):
        raise SystemExit(
            f"Python 3.14 and Node.js 20+ are required. Install {display_name} manually, then rerun setup.py."
        )
    print(f"Installing {display_name} with winget...")
    run([
        "winget", "install", "--id", package_id, "--exact",
        "--accept-package-agreements", "--accept-source-agreements",
    ])


def ensure_prerequisites() -> str:
    python = find_python()
    if not python:
        install_windows_prerequisite("Python.Python.3.14", "Python 3.14")
        python = find_python()
        if not python:
            raise SystemExit("Close the terminal after installation and rerun setup.py.")

    node = shutil.which("node")
    if not node:
        install_windows_prerequisite("OpenJS.NodeJS.LTS", "Node.js LTS")
        node = shutil.which("node")
        if not node:
            raise SystemExit("Close the terminal after installation and rerun setup.py.")

    version = subprocess.run([node, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    major = int(version.removeprefix("v").split(".", 1)[0])
    if major < 20:
        raise SystemExit(f"Node.js 20+ is required; found {version}.")
    return python


def main() -> None:
    parser = argparse.ArgumentParser(description="Install everything required to run NOVA.")
    parser.add_argument("--skip-install", action="store_true", help="Reuse existing Python and Node dependencies")
    parser.add_argument("--skip-frontend-build", action="store_true", help="Do not build the frontend")
    parser.add_argument("--include-dev", action="store_true", help="Install backend test dependencies")
    args = parser.parse_args()

    print(f"Setting up NOVA in {ROOT}")
    python = ensure_prerequisites() if not args.skip_install else sys.executable

    if not VENV_PYTHON.is_file():
        print("Creating backend/.venv...")
        run([python, "-m", "venv", str(VENV)])

    if not args.skip_install:
        print("Installing backend dependencies...")
        run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
        run([str(VENV_PYTHON), "-m", "pip", "install", "-r", "backend/requirements.txt"], cwd=ROOT)
        if args.include_dev:
            run([str(VENV_PYTHON), "-m", "pip", "install", "-r", "backend/requirements-dev.txt"], cwd=ROOT)

        print("Installing frontend dependencies...")
        run(["npm", "ci"], cwd=ROOT / "frontend")

    if not args.skip_frontend_build:
        print("Building frontend...")
        run(["npm", "run", "build"], cwd=ROOT / "frontend")

    env_file = ROOT / "backend" / ".env"
    if not env_file.is_file():
        env_file.write_bytes((ROOT / "backend" / ".env.example").read_bytes())
        print("Created backend/.env from backend/.env.example.")

    print("\nNOVA setup complete.")
    print("Start it with:")
    print("  python start.py")
    print("Then open http://127.0.0.1:8000")
    print("Configure one or more model keys in backend/.env before using AI features.")


if __name__ == "__main__":
    main()
