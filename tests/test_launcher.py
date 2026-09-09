from __future__ import annotations

import sys
from pathlib import Path

from automated_strain_rate.launcher import streamlit_command


def test_streamlit_command_targets_packaged_application() -> None:
    command = streamlit_command(("--server.port=9999",))

    assert command[:4] == [sys.executable, "-m", "streamlit", "run"]
    assert Path(command[4]).name == "app.py"
    assert Path(command[4]).is_file()
    assert command[5:] == ["--server.port=9999"]
