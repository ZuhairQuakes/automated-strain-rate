from __future__ import annotations

import numpy as np
import xarray as xr

from automated_strain_rate.anomaly import (
    AnomalyConfig,
    detect_anomalies,
    prepare_strain_field,
    regions_geojson,
    sensitivity_summary,
)


def _dataset(values: np.ndarray) -> xr.Dataset:
    return xr.Dataset(
        {"tensor_magnitude": (("latitude", "longitude"), values)},
        coords={
            "longitude": 100.0 + np.arange(values.shape[1]),
            "latitude": -4.0 + np.arange(values.shape[0]),
        },
        attrs={"strain_rate_unit": "microstrain/yr"},
    )


def test_uniform_field_has_no_false_regions() -> None:
    result = detect_anomalies(
        _dataset(np.ones((10, 10))), AnomalyConfig(percentile=95, minimum_cells=1)
    )

    assert not result.regions
    assert not result.anomaly_mask.any()


def test_known_blob_has_correct_centroid_and_statistics() -> None:
    values = np.zeros((10, 10))
    values[3:6, 4:7] = 10.0

    result = detect_anomalies(_dataset(values), AnomalyConfig(percentile=90, minimum_cells=3))

    assert len(result.regions) == 1
    region = result.regions[0]
    assert region.cell_count == 9
    assert region.centroid_longitude == 105.0
    assert region.centroid_latitude == 0.0
    assert region.maximum_strain == 10.0
    assert region.mean_strain == 10.0
    assert region.maximum_strain_percentile == 100.0
    assert region.area_km2 > 0


def test_two_anomalies_remain_separate() -> None:
    values = np.zeros((12, 12))
    values[2:5, 2:5] = 8.0
    values[8:11, 8:11] = 12.0

    result = detect_anomalies(
        _dataset(values), AnomalyConfig(percentile=80, minimum_cells=3, connectivity=8)
    )

    assert len(result.regions) == 2
    assert sorted(region.cell_count for region in result.regions) == [9, 9]


def test_nan_cells_remain_masked_during_smoothing() -> None:
    values = np.arange(100, dtype=float).reshape(10, 10)
    values[4:6, 4:6] = np.nan
    grid = prepare_strain_field(
        _dataset(values), AnomalyConfig(gaussian_sigma_cells=1.0, minimum_cells=1)
    )

    assert np.isnan(grid.original[4:6, 4:6]).all()
    assert np.isnan(grid.processed[4:6, 4:6]).all()
    assert np.isfinite(grid.processed[grid.valid_mask]).all()


def test_boundary_anomaly_is_detected_and_exported() -> None:
    values = np.zeros((10, 10))
    values[:2, :2] = 15.0
    result = detect_anomalies(_dataset(values), AnomalyConfig(percentile=95, minimum_cells=3))
    geojson = regions_geojson(result)

    assert len(result.regions) == 1
    assert result.regions[0].cell_count == 4
    assert geojson["type"] == "FeatureCollection"
    assert geojson["features"][0]["geometry"]["type"] == "MultiPolygon"


def test_threshold_sensitivity_reports_changing_region_size() -> None:
    y, x = np.mgrid[-2:2:21j, -2:2:21j]
    values = np.exp(-(x**2 + y**2))

    summary = sensitivity_summary(
        _dataset(values),
        (90.0, 95.0, 99.0),
        config=AnomalyConfig(minimum_cells=1),
    )

    counts = [row["anomalous_cell_count"] for row in summary]
    assert counts[0] > counts[1] > counts[2]
    assert all(row["zone_count"] == 1 for row in summary)


def test_robust_mad_threshold_detects_extreme_cell() -> None:
    values = np.arange(100, dtype=float).reshape(10, 10)
    values[5, 5] = 1_000.0

    result = detect_anomalies(
        _dataset(values),
        AnomalyConfig(method="robust-z", robust_z_threshold=6.0, minimum_cells=1),
    )

    assert len(result.regions) == 1
    assert result.regions[0].cell_count == 1
    assert result.regions[0].maximum_strain == 1_000.0
