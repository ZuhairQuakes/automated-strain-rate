"""Deterministic data export for the browser-only results viewer."""

from __future__ import annotations

import numpy as np

from automated_strain_rate.anomaly import detect_anomalies, regions_geojson
from automated_strain_rate.demo import synthetic_investigation_data


def _rounded(value: float) -> float:
    return round(float(value), 6)


def build_static_demo_payload() -> dict[str, object]:
    """Return compact static data derived from the tested numerical demonstration."""
    dataset, earthquakes = synthetic_investigation_data()
    result = detect_anomalies(dataset)
    longitude_grid, latitude_grid = np.meshgrid(result.grid.longitude, result.grid.latitude)
    sample = np.zeros_like(result.grid.valid_mask, dtype=bool)
    sample[::4, ::4] = True
    valid = result.grid.valid_mask & sample
    strain = [
        [_rounded(longitude), _rounded(latitude), _rounded(value)]
        for longitude, latitude, value in zip(
            longitude_grid[valid],
            latitude_grid[valid],
            result.grid.processed[valid],
            strict=True,
        )
    ]
    events = [
        {
            "id": str(row.event_id),
            "longitude": _rounded(row.longitude),
            "latitude": _rounded(row.latitude),
            "magnitude": _rounded(row.magnitude),
            "depth_km": _rounded(row.depth),
            "date": row.time.strftime("%Y-%m-%d"),
        }
        for row in earthquakes.itertuples(index=False)
    ]
    finite = result.grid.processed[result.grid.valid_mask]
    return {
        "metadata": {
            "source": "Deterministic synthetic validation field; not an observation",
            "variable": result.grid.variable,
            "unit": result.grid.units,
            "threshold_percentile": result.config.percentile,
            "threshold_value": _rounded(result.threshold_value),
            "display_min": _rounded(float(np.min(finite))),
            "display_max": _rounded(float(np.percentile(finite, 99.5))),
        },
        "bounds": [[15.8, 94.8], [28.2, 98.2]],
        "strain": strain,
        "candidate_regions": regions_geojson(result),
        "earthquakes": events,
    }
