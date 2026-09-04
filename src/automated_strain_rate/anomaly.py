"""Experimental, interpretable segmentation of numerical strain-rate fields."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr
from scipy import ndimage

DEFAULT_VARIABLE = "tensor_magnitude"
_LONGITUDE_NAMES = ("longitude", "lon", "x")
_LATITUDE_NAMES = ("latitude", "lat", "y")


@dataclass(frozen=True)
class AnomalyConfig:
    """Configurable preprocessing and segmentation parameters."""

    variable: str = DEFAULT_VARIABLE
    method: str = "percentile"
    percentile: float = 95.0
    robust_z_threshold: float = 3.5
    gaussian_sigma_cells: float = 0.0
    minimum_cells: int = 3
    opening_iterations: int = 0
    closing_iterations: int = 0
    connectivity: int = 8

    def validate(self) -> None:
        if self.method not in {"percentile", "robust-z"}:
            raise ValueError("method must be 'percentile' or 'robust-z'.")
        if not 0.0 < self.percentile < 100.0:
            raise ValueError("percentile must be between 0 and 100.")
        if self.robust_z_threshold <= 0:
            raise ValueError("robust_z_threshold must be greater than zero.")
        if self.gaussian_sigma_cells < 0:
            raise ValueError("gaussian_sigma_cells cannot be negative.")
        if self.minimum_cells < 1:
            raise ValueError("minimum_cells must be at least one.")
        if self.opening_iterations < 0 or self.closing_iterations < 0:
            raise ValueError("morphology iterations cannot be negative.")
        if self.connectivity not in {4, 8}:
            raise ValueError("connectivity must be 4 or 8.")


@dataclass(frozen=True)
class AnalysisGrid:
    """A numerical strain field with geographic coordinates and provenance."""

    variable: str
    units: str
    longitude: np.ndarray
    latitude: np.ndarray
    original: np.ndarray
    processed: np.ndarray
    valid_mask: np.ndarray


@dataclass(frozen=True)
class CandidateRegion:
    """Descriptive statistics for one connected raster region."""

    region_id: int
    centroid_longitude: float
    centroid_latitude: float
    cell_count: int
    area_km2: float
    maximum_strain: float
    mean_strain: float
    maximum_strain_percentile: float
    west: float
    east: float
    south: float
    north: float

    def properties(self) -> dict[str, int | float]:
        return {
            "zone_id": self.region_id,
            "centroid_longitude": self.centroid_longitude,
            "centroid_latitude": self.centroid_latitude,
            "cell_count": self.cell_count,
            "area_km2": self.area_km2,
            "maximum_strain": self.maximum_strain,
            "mean_strain": self.mean_strain,
            "maximum_strain_percentile": self.maximum_strain_percentile,
            "west": self.west,
            "east": self.east,
            "south": self.south,
            "north": self.north,
        }


@dataclass(frozen=True)
class DetectionResult:
    """The source field, binary segmentation, labels, and extracted regions."""

    grid: AnalysisGrid
    config: AnomalyConfig
    threshold_value: float
    labels: np.ndarray
    regions: tuple[CandidateRegion, ...]

    @property
    def anomaly_mask(self) -> np.ndarray:
        return self.labels > 0


def _coordinate_name(data: xr.DataArray, candidates: tuple[str, ...], kind: str) -> str:
    name = next((candidate for candidate in candidates if candidate in data.coords), None)
    if name is None:
        raise ValueError(f"Could not identify a {kind} coordinate for {data.name!r}.")
    return name


def _validate_coordinate(values: np.ndarray, name: str) -> np.ndarray:
    coordinate = np.asarray(values, dtype=float)
    if coordinate.ndim != 1 or coordinate.size < 2:
        raise ValueError(f"{name} must be one-dimensional with at least two cells.")
    if not np.all(np.isfinite(coordinate)):
        raise ValueError(f"{name} contains non-finite coordinates.")
    differences = np.diff(coordinate)
    if not (np.all(differences > 0) or np.all(differences < 0)):
        raise ValueError(f"{name} must be strictly monotonic.")
    return coordinate


def _nan_aware_gaussian(values: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    if sigma == 0:
        return values.copy()
    numerator = ndimage.gaussian_filter(np.where(valid, values, 0.0), sigma=sigma, mode="nearest")
    denominator = ndimage.gaussian_filter(valid.astype(float), sigma=sigma, mode="nearest")
    smoothed = np.full_like(values, np.nan, dtype=float)
    np.divide(numerator, denominator, out=smoothed, where=denominator > 0)
    smoothed[~valid] = np.nan
    return smoothed


def prepare_strain_field(
    source: str | Path | xr.Dataset,
    config: AnomalyConfig | None = None,
) -> AnalysisGrid:
    """Read and validate one 2-D NetCDF variable without altering its source values."""
    selected = config or AnomalyConfig()
    selected.validate()
    if isinstance(source, xr.Dataset):
        dataset = source
    else:
        with xr.open_dataset(source) as opened:
            dataset = opened.load()
    if selected.variable not in dataset:
        available = ", ".join(sorted(dataset.data_vars))
        raise ValueError(
            f"Variable {selected.variable!r} is unavailable. NetCDF variables: {available}."
        )
    data = dataset[selected.variable].squeeze(drop=True)
    longitude_name = _coordinate_name(data, _LONGITUDE_NAMES, "longitude")
    latitude_name = _coordinate_name(data, _LATITUDE_NAMES, "latitude")
    if data.ndim != 2 or set(data.dims) != {latitude_name, longitude_name}:
        raise ValueError(
            f"{selected.variable!r} must be a 2-D latitude/longitude field; dims={data.dims}."
        )
    ordered = data.transpose(latitude_name, longitude_name)
    longitude = _validate_coordinate(ordered[longitude_name].to_numpy(), "longitude")
    latitude = _validate_coordinate(ordered[latitude_name].to_numpy(), "latitude")
    original = np.asarray(ordered.to_numpy(), dtype=float)
    valid = np.isfinite(original)
    if not np.any(valid):
        raise ValueError(f"{selected.variable!r} contains no finite cells.")
    processed = _nan_aware_gaussian(original, valid, selected.gaussian_sigma_cells)
    return AnalysisGrid(
        variable=selected.variable,
        units=str(data.attrs.get("units", dataset.attrs.get("strain_rate_unit", "unknown"))),
        longitude=longitude,
        latitude=latitude,
        original=original,
        processed=processed,
        valid_mask=valid,
    )


def _cell_edges(coordinate: np.ndarray) -> np.ndarray:
    midpoints = (coordinate[:-1] + coordinate[1:]) / 2.0
    return np.concatenate(
        (
            [coordinate[0] - (midpoints[0] - coordinate[0])],
            midpoints,
            [coordinate[-1] + (coordinate[-1] - midpoints[-1])],
        )
    )


def geographic_bounds(grid: AnalysisGrid) -> tuple[float, float, float, float]:
    """Return west, east, south, and north edges of the raster footprint."""
    longitude_edges = _cell_edges(grid.longitude)
    latitude_edges = _cell_edges(grid.latitude)
    return (
        float(longitude_edges.min()),
        float(longitude_edges.max()),
        float(latitude_edges.min()),
        float(latitude_edges.max()),
    )


def _cell_areas_km2(longitude: np.ndarray, latitude: np.ndarray) -> np.ndarray:
    try:
        from pyproj import Geod
    except ImportError as exc:  # pragma: no cover - exercised by installation guidance
        message = "Install the investigation extra: pip install '.[investigation]'"
        raise RuntimeError(message) from exc
    geod = Geod(ellps="WGS84")
    lon_edges = _cell_edges(longitude)
    lat_edges = _cell_edges(latitude)
    areas = np.empty((latitude.size, longitude.size), dtype=float)
    for row in range(latitude.size):
        for column in range(longitude.size):
            west, east = sorted((lon_edges[column], lon_edges[column + 1]))
            south, north = sorted((lat_edges[row], lat_edges[row + 1]))
            area, _ = geod.polygon_area_perimeter(
                [west, east, east, west], [south, south, north, north]
            )
            areas[row, column] = abs(area) / 1_000_000.0
    return areas


def _region_statistics(
    labels: np.ndarray,
    grid: AnalysisGrid,
) -> tuple[CandidateRegion, ...]:
    values = grid.processed[grid.valid_mask]
    lon_edges = _cell_edges(grid.longitude)
    lat_edges = _cell_edges(grid.latitude)
    cell_areas = _cell_areas_km2(grid.longitude, grid.latitude)
    regions: list[CandidateRegion] = []
    for region_id in range(1, int(labels.max()) + 1):
        rows, columns = np.where(labels == region_id)
        region_values = grid.processed[rows, columns]
        maximum = float(np.max(region_values))
        percentile = 100.0 * float(np.count_nonzero(values <= maximum)) / values.size
        west = float(min(lon_edges[columns].min(), lon_edges[columns + 1].min()))
        east = float(max(lon_edges[columns].max(), lon_edges[columns + 1].max()))
        south = float(min(lat_edges[rows].min(), lat_edges[rows + 1].min()))
        north = float(max(lat_edges[rows].max(), lat_edges[rows + 1].max()))
        regions.append(
            CandidateRegion(
                region_id=region_id,
                centroid_longitude=float(np.mean(grid.longitude[columns])),
                centroid_latitude=float(np.mean(grid.latitude[rows])),
                cell_count=int(rows.size),
                area_km2=float(cell_areas[rows, columns].sum()),
                maximum_strain=maximum,
                mean_strain=float(np.mean(region_values)),
                maximum_strain_percentile=percentile,
                west=west,
                east=east,
                south=south,
                north=north,
            )
        )
    return tuple(regions)


def detect_anomalies(
    source: str | Path | xr.Dataset | AnalysisGrid,
    config: AnomalyConfig | None = None,
) -> DetectionResult:
    """Threshold and label coherent high-value regions in a numerical strain field."""
    selected = config or AnomalyConfig()
    selected.validate()
    grid = source if isinstance(source, AnalysisGrid) else prepare_strain_field(source, selected)
    finite_values = grid.processed[grid.valid_mask]
    if selected.method == "percentile":
        threshold = float(np.percentile(finite_values, selected.percentile))
        mask = grid.valid_mask & (grid.processed > threshold)
    else:
        median = float(np.median(finite_values))
        mad = float(np.median(np.abs(finite_values - median)))
        if mad == 0.0:
            threshold = float("inf")
            mask = np.zeros_like(grid.valid_mask)
        else:
            threshold = median + selected.robust_z_threshold * mad / 0.6744897501960817
            mask = grid.valid_mask & (grid.processed > threshold)

    structure = ndimage.generate_binary_structure(2, 2 if selected.connectivity == 8 else 1)
    if selected.opening_iterations:
        mask = ndimage.binary_opening(
            mask, structure=structure, iterations=selected.opening_iterations
        )
    if selected.closing_iterations:
        mask = ndimage.binary_closing(
            mask, structure=structure, iterations=selected.closing_iterations
        )
    mask &= grid.valid_mask
    labels, count = ndimage.label(mask, structure=structure)
    for region_id in range(1, count + 1):
        if np.count_nonzero(labels == region_id) < selected.minimum_cells:
            labels[labels == region_id] = 0
    labels, _ = ndimage.label(labels > 0, structure=structure)
    return DetectionResult(
        grid=grid,
        config=selected,
        threshold_value=threshold,
        labels=labels.astype(np.int32),
        regions=_region_statistics(labels, grid),
    )


def sensitivity_summary(
    source: str | Path | xr.Dataset,
    percentiles: tuple[float, ...] = (90.0, 95.0, 97.5, 99.0),
    *,
    config: AnomalyConfig | None = None,
) -> list[dict[str, Any]]:
    """Summarize how segmentation changes across percentile thresholds."""
    base = config or AnomalyConfig()
    if base.method != "percentile":
        raise ValueError("Sensitivity percentiles require method='percentile'.")
    grid = prepare_strain_field(source, base)
    rows: list[dict[str, Any]] = []
    for percentile in percentiles:
        result = detect_anomalies(grid, replace(base, percentile=float(percentile)))
        rows.append(
            {
                "percentile": float(percentile),
                "threshold_value": result.threshold_value,
                "zone_count": len(result.regions),
                "anomalous_cell_count": int(np.count_nonzero(result.labels)),
                "total_area_km2": float(sum(region.area_km2 for region in result.regions)),
                "centroids": ";".join(
                    f"{region.centroid_longitude:.6f},{region.centroid_latitude:.6f}"
                    for region in result.regions
                ),
            }
        )
    return rows


def regions_geojson(result: DetectionResult) -> dict[str, Any]:
    """Return raster-cell footprints for every connected region as GeoJSON."""
    lon_edges = _cell_edges(result.grid.longitude)
    lat_edges = _cell_edges(result.grid.latitude)
    features: list[dict[str, Any]] = []
    for region in result.regions:
        rows, columns = np.where(result.labels == region.region_id)
        polygons = []
        for row, column in zip(rows, columns, strict=True):
            west, east = sorted((lon_edges[column], lon_edges[column + 1]))
            south, north = sorted((lat_edges[row], lat_edges[row + 1]))
            polygons.append(
                [[[west, south], [east, south], [east, north], [west, north], [west, south]]]
            )
        features.append(
            {
                "type": "Feature",
                "properties": region.properties(),
                "geometry": {"type": "MultiPolygon", "coordinates": polygons},
            }
        )
    return {"type": "FeatureCollection", "features": features}
