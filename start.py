"""Start the NOVA FastAPI server."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / "backend" / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start NOVA.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if not VENV_PYTHON.is_file():
        raise SystemExit("NOVA is not set up yet. Run 'python setup.py' first.")

    command = [
        str(VENV_PYTHON), "-m", "uvicorn", "backend.main:app",
        "--host", args.host, "--port", str(args.port),
    ]
    if args.reload:
        command.append("--reload")

    print(f"Starting NOVA at http://{args.host}:{args.port}")
    try:
        raise SystemExit(subprocess.call(command, cwd=ROOT))
    except KeyboardInterrupt:
        raise SystemExit(0)


if __name__ == "__main__":
    main()
