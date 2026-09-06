from __future__ import annotations

from automated_strain_rate.static_demo import build_static_demo_payload


def test_static_payload_comes_from_deterministic_numerical_demo() -> None:
    payload = build_static_demo_payload()

    assert payload["metadata"]["threshold_percentile"] == 95.0
    assert payload["metadata"]["source"].endswith("not an observation")
    assert len(payload["candidate_regions"]["features"]) == 2
    assert len(payload["earthquakes"]) == 4
    assert 500 < len(payload["strain"]) < 1_000
