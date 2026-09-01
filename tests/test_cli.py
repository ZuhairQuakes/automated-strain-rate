from __future__ import annotations

import json
from pathlib import Path

from automated_strain_rate.cli import main


def test_inspect_command(tmp_path: Path, capsys) -> None:
    source = tmp_path / "stations.txt"
    source.write_text(
        "95 18 10 20 0 1 1 1 A\n"
        "96 19 11 21 0 1 1 1 B\n"
        "97 20 12 22 0 1 1 1 C\n",
        encoding="utf-8",
    )

    assert main(["inspect", str(source)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["stations"] == 3
