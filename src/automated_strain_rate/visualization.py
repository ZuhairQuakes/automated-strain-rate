"""Static scientific visualizations for experimental candidate-zone analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from automated_strain_rate.anomaly import DetectionResult, geographic_bounds


def _matplotlib():
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - exercised by installation guidance
        message = "Install the investigation extra: pip install '.[investigation]'"
        raise RuntimeError(message) from exc
    return plt


def plot_investigation_map(
    result: DetectionResult,
    earthquakes: pd.DataFrame,
    output: str | Path,
) -> Path:
    """Plot the numerical field, detected outlines, IDs, and earthquake observations."""
    plt = _matplotlib()
    figure, axis = plt.subplots(figsize=(10, 8), constrained_layout=True)
    mesh = axis.pcolormesh(
        result.grid.longitude,
        result.grid.latitude,
        result.grid.processed,
        shading="auto",
        cmap="magma",
    )
    colorbar = figure.colorbar(mesh, ax=axis, pad=0.02)
    smoothing = result.config.gaussian_sigma_cells
    field_label = result.grid.variable if smoothing == 0 else f"{result.grid.variable} (smoothed)"
    colorbar.set_label(f"{field_label} [{result.grid.units}]")
    if result.regions:
        axis.contour(
            result.grid.longitude,
            result.grid.latitude,
            result.labels > 0,
            levels=[0.5],
            colors="#25d0c5",
            linewidths=1.8,
        )
        for region in result.regions:
            axis.text(
                region.centroid_longitude,
                region.centroid_latitude,
                f"Z{region.region_id}",
                color="white",
                fontsize=9,
                fontweight="bold",
                ha="center",
                va="center",
                bbox={"facecolor": "#12343b", "edgecolor": "white", "alpha": 0.8},
            )
    if not earthquakes.empty:
        magnitudes = earthquakes["magnitude"].to_numpy(float)
        marker_sizes = 12.0 + 6.0 * np.maximum(magnitudes, 0.0) ** 2
        axis.scatter(
            earthquakes["longitude"],
            earthquakes["latitude"],
            s=marker_sizes,
            facecolors="none",
            edgecolors="#55d6ff",
            linewidths=1.2,
            label="Earthquakes (marker size ∝ magnitude²)",
        )
        axis.legend(loc="best")
    axis.set_xlabel("Longitude [degrees east]")
    axis.set_ylabel("Latitude [degrees north]")
    west, east, south, north = geographic_bounds(result.grid)
    axis.set_xlim(west, east)
    axis.set_ylim(south, north)
    axis.set_title("Experimental strain anomalies and observed earthquakes")
    axis.text(
        0.01,
        0.01,
        "Candidate regions for expert investigation — not earthquake forecasts",
        transform=axis.transAxes,
        fontsize=8,
        color="white",
        bbox={"facecolor": "black", "alpha": 0.65, "edgecolor": "none"},
    )
    path = Path(output)
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def plot_diagnostic(
    zones: pd.DataFrame,
    output: str | Path,
    *,
    units: str = "unknown",
) -> Path:
    """Plot anomaly strength against earthquake count without deriving a risk score."""
    plt = _matplotlib()
    figure, axis = plt.subplots(figsize=(7, 5), constrained_layout=True)
    if zones.empty:
        axis.text(0.5, 0.5, "No candidate zones detected", ha="center", va="center")
    else:
        axis.scatter(
            zones["maximum_strain"],
            zones["earthquake_count_within_buffer"],
            s=55,
            color="#087f8c",
        )
        for row in zones.itertuples(index=False):
            axis.annotate(
                f"Z{row.zone_id}",
                (row.maximum_strain, row.earthquake_count_within_buffer),
                xytext=(4, 4),
                textcoords="offset points",
            )
    axis.set_xlabel(f"Maximum strain anomaly strength [{units}]")
    axis.set_ylabel("Earthquakes within configured buffer")
    axis.set_title("Descriptive spatial association (not causation)")
    axis.grid(alpha=0.25)
    path = Path(output)
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path
