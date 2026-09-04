from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from automated_strain_rate.anomaly import AnomalyConfig, detect_anomalies
from automated_strain_rate.candidate_zones import candidate_zone_table
from automated_strain_rate.spatial_association import associate_earthquakes


def _result():
    values = np.zeros((5, 5))
    values[1:3, 1:3] = 10.0
    dataset = xr.Dataset(
        {"tensor_magnitude": (("latitude", "longitude"), values)},
        coords={"longitude": np.arange(5.0), "latitude": np.arange(5.0)},
        attrs={"strain_rate_unit": "microstrain/yr"},
    )
    return detect_anomalies(dataset, AnomalyConfig(percentile=80, minimum_cells=1))


def _catalog() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": ["inside", "near", "far"],
            "longitude": [1.0, 3.0, 20.0],
            "latitude": [1.0, 1.0, 20.0],
            "magnitude": [5.0, 6.0, 7.0],
            "time": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"], utc=True),
            "depth": [10.0, 20.0, 30.0],
        }
    )


def test_inside_buffer_and_geodesic_distance() -> None:
    summary = associate_earthquakes(_result(), _catalog(), buffer_km=120.0)[0]

    assert summary["earthquake_count_inside"] == 1
    assert summary["earthquake_count_within_buffer"] == 2
    assert summary["largest_magnitude_within_buffer"] == 6.0
    assert summary["nearest_earthquake_distance_km"] == 0.0
    assert summary["earthquake_density_per_1000_km2"] > 0


def test_no_earthquake_case() -> None:
    empty = _catalog().iloc[0:0]
    summary = associate_earthquakes(_result(), empty)[0]

    assert summary["earthquake_count_inside"] == 0
    assert np.isnan(summary["nearest_earthquake_distance_km"])


def test_candidate_table_ranks_by_strain_not_earthquakes() -> None:
    table = candidate_zone_table(_result(), _catalog(), buffer_km=120.0)

    assert table.loc[0, "anomaly_rank"] == 1
    assert table.loc[0, "maximum_strain"] == 10.0
    assert "earthquake_count_inside" in table
