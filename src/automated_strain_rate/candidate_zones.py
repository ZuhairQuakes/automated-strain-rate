"""Candidate-zone tables and reproducible output writing."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from automated_strain_rate.anomaly import DetectionResult, regions_geojson
from automated_strain_rate.spatial_association import associate_earthquakes


@dataclass(frozen=True)
class InvestigationOutputs:
    """Paths created by an experimental investigation run."""

    candidate_zones: Path
    detected_regions: Path
    map_figure: Path
    diagnostic_figure: Path
    metadata: Path
    sensitivity_summary: Path


def candidate_zone_table(
    result: DetectionResult,
    earthquakes: pd.DataFrame,
    *,
    buffer_km: float = 50.0,
) -> pd.DataFrame:
    """Build a transparent table ranked only by maximum strain."""
    region_rows = [region.properties() for region in result.regions]
    associations = associate_earthquakes(result, earthquakes, buffer_km=buffer_km)
    if not region_rows:
        columns = [
            "anomaly_rank",
            "zone_id",
            "centroid_longitude",
            "centroid_latitude",
            "maximum_strain",
            "mean_strain",
            "maximum_strain_percentile",
            "cell_count",
            "area_km2",
            "west",
            "east",
            "south",
            "north",
            "earthquake_count_inside",
            "earthquake_count_within_buffer",
            "largest_magnitude_within_buffer",
            "mean_magnitude_within_buffer",
            "nearest_earthquake_distance_km",
            "earthquake_density_per_1000_km2",
        ]
        return pd.DataFrame(columns=columns)
    table = pd.DataFrame(region_rows).merge(pd.DataFrame(associations), on="zone_id")
    table = table.sort_values(["maximum_strain", "zone_id"], ascending=[False, True]).reset_index(
        drop=True
    )
    table.insert(0, "anomaly_rank", range(1, len(table) + 1))
    return table


def write_investigation_outputs(
    result: DetectionResult,
    earthquakes: pd.DataFrame,
    sensitivity: pd.DataFrame,
    output_directory: str | Path,
    *,
    input_netcdf: str | Path,
    earthquake_metadata: dict[str, Any],
    buffer_km: float,
) -> InvestigationOutputs:
    """Write tables, raster-footprint GeoJSON, figures, and processing metadata."""
    from automated_strain_rate.visualization import plot_diagnostic, plot_investigation_map

    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    paths = InvestigationOutputs(
        candidate_zones=destination / "candidate_zones.csv",
        detected_regions=destination / "detected_regions.geojson",
        map_figure=destination / "investigation_map.png",
        diagnostic_figure=destination / "strain_vs_earthquakes.png",
        metadata=destination / "processing_metadata.json",
        sensitivity_summary=destination / "sensitivity_summary.csv",
    )
    zones = candidate_zone_table(result, earthquakes, buffer_km=buffer_km)
    zones.to_csv(paths.candidate_zones, index=False)
    paths.detected_regions.write_text(
        json.dumps(regions_geojson(result), indent=2), encoding="utf-8"
    )
    sensitivity.to_csv(paths.sensitivity_summary, index=False)
    plot_investigation_map(result, earthquakes, paths.map_figure)
    plot_diagnostic(zones, paths.diagnostic_figure, units=result.grid.units)
    metadata = {
        "experimental": True,
        "interpretation": "candidate regions for expert investigation; not a forecast",
        "created_at": datetime.now(UTC).isoformat(),
        "input_netcdf": str(Path(input_netcdf)),
        "variable": result.grid.variable,
        "units": result.grid.units,
        "preprocessing_and_detection": asdict(result.config),
        "threshold_value": result.threshold_value,
        "finite_cell_count": int(result.grid.valid_mask.sum()),
        "masked_cell_count": int((~result.grid.valid_mask).sum()),
        "candidate_zone_count": len(result.regions),
        "buffer_km": buffer_km,
        "distance_method": "WGS84 geodesic distance to nearest anomalous cell centre",
        "earthquakes": earthquake_metadata,
        "outputs": {name: path.name for name, path in asdict(paths).items()},
        "scientific_warning": (
            "Spatial coincidence between high strain rate and earthquakes does not demonstrate "
            "causality and this tool does not provide earthquake forecasts or operational hazard "
            "assessments."
        ),
    }
    paths.metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return paths
