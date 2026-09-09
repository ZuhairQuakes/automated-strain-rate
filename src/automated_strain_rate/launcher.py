"""Installed launcher for the optional Streamlit application."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def streamlit_command(arguments: Sequence[str] = ()) -> list[str]:
    """Return the interpreter-safe command for the packaged application."""
    app_path = Path(__file__).with_name("app.py")
    return [sys.executable, "-m", "streamlit", "run", str(app_path), *arguments]


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the installed web application and forward Streamlit options."""
    if importlib.util.find_spec("streamlit") is None:
        print(
            "The web application is optional. Install it with: "
            'pip install "automated-strain-rate[app]"',
            file=sys.stderr,
        )
        return 2
    completed = subprocess.run(streamlit_command(argv or sys.argv[1:]), check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
