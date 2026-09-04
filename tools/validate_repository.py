#!/usr/bin/env python3
"""Dependency-free structural checks for this research repository."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".ipynb_checkpoints",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "venv",
}
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REQUIRED_PROJECT_FILES = {
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "EXPERIMENTAL_ANOMALY_EXPLORER.md",
    "LICENSE",
    "README.md",
    "SCIENTIFIC_METHOD.md",
    "SECURITY.md",
    "SUPPORT.md",
    "pyproject.toml",
}


def files_with_suffix(suffix: str):
    for path in ROOT.rglob(f"*{suffix}"):
        if not any(part in SKIP_DIRS for part in path.parts):
            yield path


def validate_python(errors: list[str]) -> int:
    count = 0
    for path in files_with_suffix(".py"):
        count += 1
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (SyntaxError, UnicodeDecodeError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    return count


def validate_json(errors: list[str]) -> tuple[int, int]:
    json_count = 0
    notebook_count = 0
    for path in files_with_suffix(".json"):
        json_count += 1
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    for path in files_with_suffix(".ipynb"):
        notebook_count += 1
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"))
            if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
                errors.append(f"{path.relative_to(ROOT)}: unsupported notebook structure")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    return json_count, notebook_count


def validate_markdown_links(errors: list[str]) -> int:
    count = 0
    for path in files_with_suffix(".md"):
        count += 1
        text = path.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            local_target = unquote(target.split("#", 1)[0])
            if local_target and not (path.parent / local_target).resolve().exists():
                errors.append(f"{path.relative_to(ROOT)}: missing local link {target!r}")
    return count


def validate_project_structure(errors: list[str]) -> None:
    for relative_path in sorted(REQUIRED_PROJECT_FILES):
        if not (ROOT / relative_path).is_file():
            errors.append(f"missing required project file: {relative_path}")
    package_init = ROOT / "src/automated_strain_rate/__init__.py"
    if not package_init.is_file():
        errors.append("missing Python package: src/automated_strain_rate")
    elif '__version__ = "0.2.0"' not in package_init.read_text(encoding="utf-8"):
        errors.append("package version is not synchronized with the 0.2.0 release")


def main() -> int:
    errors: list[str] = []
    validate_project_structure(errors)
    python_count = validate_python(errors)
    json_count, notebook_count = validate_json(errors)
    markdown_count = validate_markdown_links(errors)
    print(
        f"Checked {python_count} Python files, {notebook_count} notebooks, "
        f"{json_count} JSON files, and {markdown_count} Markdown files."
    )
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
