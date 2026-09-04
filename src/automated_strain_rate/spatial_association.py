"""Transparent spatial association between raster anomalies and earthquakes."""

from __future__ import annotations

import numpy as np
import pandas as pd

from automated_strain_rate.anomaly import DetectionResult


def _nearest_indices(coordinate: np.ndarray, values: np.ndarray) -> np.ndarray:
    return np.abs(coordinate[:, np.newaxis] - values[np.newaxis, :]).argmin(axis=0)


def _coordinate_limits(coordinate: np.ndarray) -> tuple[float, float]:
    midpoints = (coordinate[:-1] + coordinate[1:]) / 2.0
    edges = np.concatenate(
        (
            [coordinate[0] - (midpoints[0] - coordinate[0])],
            midpoints,
            [coordinate[-1] + (coordinate[-1] - midpoints[-1])],
        )
    )
    return float(np.min(edges)), float(np.max(edges))


def associate_earthquakes(
    result: DetectionResult,
    earthquakes: pd.DataFrame,
    *,
    buffer_km: float = 50.0,
) -> list[dict[str, int | float]]:
    """Calculate descriptive earthquake statistics for every detected region.

    "Inside" uses raster-cell membership. Buffer distances use WGS84 geodesic
    distances to the nearest anomalous cell centre, with inside events assigned
    zero distance. This avoids treating longitude/latitude degrees as kilometres.
    """
    if not np.isfinite(buffer_km) or buffer_km < 0:
        raise ValueError("buffer_km must be a non-negative finite number.")
    try:
        from pyproj import Geod
    except ImportError as exc:  # pragma: no cover - exercised by installation guidance
        message = "Install the investigation extra: pip install '.[investigation]'"
        raise RuntimeError(message) from exc

    required = {"longitude", "latitude", "magnitude", "time", "depth"}
    missing = sorted(required - set(earthquakes.columns))
    if missing:
        raise ValueError(f"Earthquake catalogue is missing columns: {', '.join(missing)}.")
    if earthquakes.empty:
        return [
            {
                "zone_id": region.region_id,
                "earthquake_count_inside": 0,
                "earthquake_count_within_buffer": 0,
                "largest_magnitude_within_buffer": float("nan"),
                "mean_magnitude_within_buffer": float("nan"),
                "nearest_earthquake_distance_km": float("nan"),
                "earthquake_density_per_1000_km2": 0.0,
            }
            for region in result.regions
        ]

    eq_lon = earthquakes["longitude"].to_numpy(float)
    eq_lat = earthquakes["latitude"].to_numpy(float)
    eq_magnitude = earthquakes["magnitude"].to_numpy(float)
    lon_indices = _nearest_indices(result.grid.longitude, eq_lon)
    lat_indices = _nearest_indices(result.grid.latitude, eq_lat)
    lon_min, lon_max = _coordinate_limits(result.grid.longitude)
    lat_min, lat_max = _coordinate_limits(result.grid.latitude)
    within_grid = (
        (eq_lon >= lon_min) & (eq_lon <= lon_max) & (eq_lat >= lat_min) & (eq_lat <= lat_max)
    )
    geod = Geod(ellps="WGS84")
    summaries: list[dict[str, int | float]] = []
    for region in result.regions:
        inside = within_grid & (result.labels[lat_indices, lon_indices] == region.region_id)
        rows, columns = np.where(result.labels == region.region_id)
        cell_lon = result.grid.longitude[columns]
        cell_lat = result.grid.latitude[rows]
        distances = np.empty(len(earthquakes), dtype=float)
        for index, (longitude, latitude) in enumerate(zip(eq_lon, eq_lat, strict=True)):
            _, _, metres = geod.inv(
                np.full(cell_lon.shape, longitude),
                np.full(cell_lat.shape, latitude),
                cell_lon,
                cell_lat,
            )
            distances[index] = 0.0 if inside[index] else float(np.min(metres)) / 1_000.0
        buffered = distances <= buffer_km
        magnitudes = eq_magnitude[buffered]
        inside_count = int(np.count_nonzero(inside))
        density = 1_000.0 * inside_count / region.area_km2 if region.area_km2 else float("nan")
        summaries.append(
            {
                "zone_id": region.region_id,
                "earthquake_count_inside": inside_count,
                "earthquake_count_within_buffer": int(np.count_nonzero(buffered)),
                "largest_magnitude_within_buffer": (
                    float(np.max(magnitudes)) if magnitudes.size else float("nan")
                ),
                "mean_magnitude_within_buffer": (
                    float(np.mean(magnitudes)) if magnitudes.size else float("nan")
                ),
                "nearest_earthquake_distance_km": float(np.min(distances)),
                "earthquake_density_per_1000_km2": float(density),
            }
        )
    return summaries
