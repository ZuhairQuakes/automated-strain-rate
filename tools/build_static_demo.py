#!/usr/bin/env python3
"""Build the browser-only demonstration data from the tested numerical package."""

from __future__ import annotations

import json
from pathlib import Path

from automated_strain_rate.static_demo import build_static_demo_payload

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/data/demo-results.js"

def main() -> int:
    """Write a JavaScript data bundle that works without API calls."""
    payload = json.dumps(build_static_demo_payload(), separators=(",", ":"), allow_nan=False)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(f"window.AUTOMATED_STRAIN_RATE_DEMO={payload};\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
