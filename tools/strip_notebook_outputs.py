#!/usr/bin/env python3
"""Remove execution state and outputs from one or more Jupyter notebooks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def strip_outputs(path: Path) -> int:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("outputs") or cell.get("execution_count") is not None:
            changed += 1
        cell["outputs"] = []
        cell["execution_count"] = None
    notebook.get("metadata", {}).pop("widgets", None)
    path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebooks", nargs="+", type=Path)
    args = parser.parse_args()
    for notebook in args.notebooks:
        changed = strip_outputs(notebook)
        print(f"{notebook}: stripped execution state from {changed} code cells")


if __name__ == "__main__":
    main()
