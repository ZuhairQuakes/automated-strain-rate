"""Streamlit interface for experimental strain-anomaly investigation."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import asdict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import xarray as xr

from automated_strain_rate.anomaly import (
    AnomalyConfig,
    DetectionResult,
    detect_anomalies,
    geographic_bounds,
    regions_geojson,
    sensitivity_summary,
)
from automated_strain_rate.candidate_zones import candidate_zone_table
from automated_strain_rate.demo import synthetic_investigation_data
from automated_strain_rate.earthquakes import (
    REQUIRED_COLUMNS,
    normalize_earthquake_catalog,
)

_MAGMA_COLORS = (
    "#020106",
    "#180f3d",
    "#440f76",
    "#721f81",
    "#9e2f7f",
    "#cd4071",
    "#f1605d",
    "#fd9668",
    "#feca8d",
    "#fcfdbf",
)
_MAGMA_COLORSCALE = tuple(
    (index / (len(_MAGMA_COLORS) - 1), color) for index, color in enumerate(_MAGMA_COLORS)
)
_WORLD_IMAGERY_TILES = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
_PB2002_BOUNDARIES_GEOJSON = (
    "https://raw.githubusercontent.com/fraxen/tectonicplates/master/GeoJSON/PB2002_boundaries.json"
)


def _uploaded_dataset(uploaded) -> xr.Dataset:
    with xr.open_dataset(io.BytesIO(uploaded.getvalue())) as opened:
        return opened.load()


def _uploaded_catalog(uploaded) -> pd.DataFrame:
    return normalize_earthquake_catalog(pd.read_csv(io.BytesIO(uploaded.getvalue())))


def _upload_provenance(uploaded) -> dict[str, str | int]:
    content = uploaded.getvalue()
    return {
        "name": uploaded.name,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _display_range(result: DetectionResult) -> tuple[float, float]:
    finite = result.grid.processed[result.grid.valid_mask]
    lower = float(np.min(finite))
    upper = float(np.percentile(finite, 99.5))
    if upper <= lower:
        padding = max(abs(lower) * 0.01, 1e-12)
        lower -= padding
        upper += padding
    return lower, upper


def _coordinate_edges(coordinate: np.ndarray) -> np.ndarray:
    midpoints = (coordinate[:-1] + coordinate[1:]) / 2.0
    return np.concatenate(
        (
            [coordinate[0] - (midpoints[0] - coordinate[0])],
            midpoints,
            [coordinate[-1] + (coordinate[-1] - midpoints[-1])],
        )
    )


def _region_outline_coordinates(
    result: DetectionResult,
) -> tuple[list[float | None], list[float | None]]:
    longitude_edges = _coordinate_edges(result.grid.longitude)
    latitude_edges = _coordinate_edges(result.grid.latitude)
    longitudes: list[float | None] = []
    latitudes: list[float | None] = []
    rows, columns = result.labels.shape

    def add_edge(lon_a: float, lat_a: float, lon_b: float, lat_b: float) -> None:
        longitudes.extend((lon_a, lon_b, None))
        latitudes.extend((lat_a, lat_b, None))

    for row, column in zip(*np.where(result.labels > 0), strict=True):
        region_id = result.labels[row, column]
        west, east = longitude_edges[column : column + 2]
        south, north = latitude_edges[row : row + 2]
        if row == 0 or result.labels[row - 1, column] != region_id:
            add_edge(west, south, east, south)
        if row == rows - 1 or result.labels[row + 1, column] != region_id:
            add_edge(west, north, east, north)
        if column == 0 or result.labels[row, column - 1] != region_id:
            add_edge(west, south, west, north)
        if column == columns - 1 or result.labels[row, column + 1] != region_id:
            add_edge(east, south, east, north)
    return longitudes, latitudes


def _map_figure(result: DetectionResult, earthquakes: pd.DataFrame) -> go.Figure:
    west, east, south, north = geographic_bounds(result.grid)
    color_min, color_max = _display_range(result)
    outline_longitudes, outline_latitudes = _region_outline_coordinates(result)
    longitude_grid, latitude_grid = np.meshgrid(result.grid.longitude, result.grid.latitude)
    valid = result.grid.valid_mask
    strain_values = result.grid.processed[valid]
    normalized = np.clip((strain_values - color_min) / (color_max - color_min), 0.0, 1.0)
    marker_opacity = 0.03 + 0.85 * normalized**0.9
    figure = go.Figure()
    figure.add_trace(
        go.Scattermap(
            lon=[None],
            lat=[None],
            mode="lines",
            line={"color": "#ffd166", "width": 2},
            hoverinfo="skip",
            name="PB2002 plate boundaries",
        )
    )
    figure.add_trace(
        go.Scattermap(
            lon=longitude_grid[valid],
            lat=latitude_grid[valid],
            mode="markers",
            marker={
                "size": 7,
                "opacity": marker_opacity,
                "color": strain_values,
                "cmin": color_min,
                "cmax": color_max,
                "colorscale": _MAGMA_COLORSCALE,
                "showscale": True,
                "colorbar": {
                    "title": {"text": f"{result.grid.variable}<br>{result.grid.units}"},
                    "thickness": 16,
                    "len": 0.72,
                },
            },
            customdata=strain_values,
            hovertemplate=(
                "Lon %{lon:.3f}°<br>Lat %{lat:.3f}°<br>Strain %{customdata:.5g} "
                f"{result.grid.units}<extra></extra>"
            ),
            showlegend=False,
            name="Strain values",
        )
    )
    if result.regions:
        figure.add_trace(
            go.Scattermap(
                lon=outline_longitudes,
                lat=outline_latitudes,
                mode="lines",
                line={"color": "#4de3d5", "width": 3},
                hoverinfo="skip",
                name="Candidate-region outline",
            )
        )
        figure.add_trace(
            go.Scattermap(
                lon=[region.centroid_longitude for region in result.regions],
                lat=[
                    region.centroid_latitude - 0.025 * (north - south) for region in result.regions
                ],
                text=[f"Z{region.region_id}" for region in result.regions],
                customdata=np.array(
                    [
                        [region.maximum_strain, region.mean_strain, region.area_km2]
                        for region in result.regions
                    ]
                ),
                mode="text",
                textposition="middle center",
                textfont={"color": "#4de3d5", "size": 13},
                hovertemplate=(
                    "%{text}<br>Maximum %{customdata[0]:.5g}<br>Mean %{customdata[1]:.5g}"
                    "<br>Area %{customdata[2]:,.1f} km²<extra></extra>"
                ),
                showlegend=False,
                name="Candidate-zone labels",
            )
        )
    if not earthquakes.empty:
        magnitudes = earthquakes["magnitude"].to_numpy(float)
        marker_sizes = np.clip(5.0 + 2.6 * magnitudes, 8.0, 28.0)
        event_dates = pd.to_datetime(earthquakes["time"], utc=True).dt.strftime("%Y-%m-%d")
        custom = list(
            zip(
                earthquakes["event_id"].astype(str),
                earthquakes["time"].astype(str),
                earthquakes["depth"].to_numpy(float),
                magnitudes,
                strict=True,
            )
        )
        figure.add_trace(
            go.Scattermap(
                lon=earthquakes["longitude"],
                lat=earthquakes["latitude"],
                mode="markers",
                marker={"size": marker_sizes + 5, "color": "#f8fafc", "opacity": 0.95},
                hoverinfo="skip",
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scattermap(
                lon=earthquakes["longitude"],
                lat=earthquakes["latitude"],
                mode="markers+text" if len(earthquakes) <= 20 else "markers",
                text=[
                    f"M{magnitude:.1f} · {date}"
                    for magnitude, date in zip(magnitudes, event_dates, strict=True)
                ],
                textposition="top right",
                textfont={"color": "#dbeafe", "size": 11},
                marker={"size": marker_sizes, "color": "#2563a7", "opacity": 0.95},
                customdata=custom,
                hovertemplate=(
                    "%{customdata[0]}<br>Mw %{customdata[3]:.1f}<br>Depth %{customdata[2]:.1f} km"
                    "<br>%{customdata[1]}<extra></extra>"
                ),
                name="Earthquakes",
            )
        )
    figure.update_layout(
        template="plotly_dark",
        height=720,
        margin={"l": 10, "r": 10, "t": 35, "b": 10},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "x": 0},
        map={
            "style": "white-bg",
            "layers": [
                {
                    "sourcetype": "raster",
                    "source": [_WORLD_IMAGERY_TILES],
                    "below": "traces",
                    "sourceattribution": "Esri World Imagery",
                },
                {
                    "sourcetype": "geojson",
                    "source": _PB2002_BOUNDARIES_GEOJSON,
                    "type": "line",
                    "color": "#ffd166",
                    "line": {"width": 2},
                },
            ],
            "center": {"lon": (west + east) / 2.0, "lat": (south + north) / 2.0},
            "zoom": float(
                np.clip(np.log2(360.0 / max(east - west, north - south)) + 0.1, 1.0, 10.0)
            ),
        },
        hovermode="closest",
    )
    return figure


def _sensitivity_figure(summary: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=summary["percentile"],
            y=summary["total_area_km2"],
            name="Candidate area",
            marker_color="#239a91",
            yaxis="y",
            hovertemplate="%{x:g}th percentile<br>%{y:,.1f} km²<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=summary["percentile"],
            y=summary["zone_count"],
            name="Region count",
            mode="lines+markers+text",
            text=summary["zone_count"],
            textposition="top center",
            line={"color": "#f2b84b", "width": 3},
            yaxis="y2",
            hovertemplate="%{x:g}th percentile<br>%{y:g} regions<extra></extra>",
        )
    )
    figure.update_layout(
        template="plotly_dark",
        height=430,
        margin={"l": 10, "r": 10, "t": 35, "b": 10},
        xaxis={"title": "Anomaly threshold [percentile]"},
        yaxis={"title": "Total candidate area [km²]"},
        yaxis2={
            "title": "Connected region count",
            "overlaying": "y",
            "side": "right",
            "rangemode": "tozero",
        },
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "x": 0},
    )
    return figure


def _header() -> None:
    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">EXPERIMENTAL RESEARCH INTERFACE</div>
          <h1>Strain anomaly + earthquake explorer</h1>
          <p>Inspect numerical strain concentrations, connected candidate regions,
          earthquake observations, and threshold sensitivity.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def run() -> None:
    st.set_page_config(page_title="Strain Anomaly Explorer", page_icon="🧭", layout="wide")
    st.markdown(
        """
        <style>
        .stApp {background: linear-gradient(145deg, #07131f 0%, #102c3b 58%, #173f42 100%);}
        [data-testid="stSidebar"] {background: #081924; border-right: 1px solid #244556;}
        .hero {padding: 2rem 2.2rem; border: 1px solid #31586a; border-radius: 18px;
               background: linear-gradient(120deg, rgba(8,25,36,.96), rgba(15,62,66,.87));
               margin-bottom: 1rem;}
        .hero h1 {font-size: clamp(2rem, 4vw, 3.6rem); line-height: 1.05; margin: .3rem 0 .8rem;
                  letter-spacing: -.035em; color: #f4f7f1;}
        .hero p {font-size: 1.05rem; color: #b8d0d3; max-width: 850px; margin: 0;}
        .eyebrow {color: #49d6b4; font-weight: 700; letter-spacing: .15em; font-size: .75rem;}
        [data-testid="stMetric"] {background: rgba(7,24,34,.72); border: 1px solid #294d5e;
                                  border-radius: 14px; padding: .75rem 1rem;}
        div[data-testid="stAlert"] {border-radius: 12px;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.header("Input data")
        source_mode = st.radio("Strain field", ("Synthetic demonstration", "Upload NetCDF"))
        if source_mode == "Synthetic demonstration":
            dataset, demo_earthquakes = synthetic_investigation_data()
            strain_source: dict[str, str | int] = {"source": "synthetic demonstration v1"}
            st.caption("Deterministic test field—not an observation.")
        else:
            uploaded_grid = st.file_uploader("NetCDF strain field", type=("nc", "netcdf"))
            if uploaded_grid is None:
                st.info("Upload a NetCDF file to begin.")
                st.stop()
            try:
                dataset = _uploaded_dataset(uploaded_grid)
            except (OSError, ValueError) as exc:
                st.error(f"Could not read the NetCDF file: {exc}")
                st.stop()
            strain_source = {"source": "uploaded NetCDF", **_upload_provenance(uploaded_grid)}
            demo_earthquakes = pd.DataFrame(columns=["event_id", *REQUIRED_COLUMNS])
        if "tensor_magnitude" not in dataset:
            st.error("The MVP requires the NetCDF variable 'tensor_magnitude'.")
            st.stop()
        variable = "tensor_magnitude"
        st.text_input("Numerical strain variable", variable, disabled=True)

        st.divider()
        st.header("Anomaly definition")
        method = st.selectbox("Method", ("percentile", "robust-z"))
        percentile = st.slider("Percentile", 80.0, 99.5, 95.0, 0.5, disabled=method != "percentile")
        robust_z = st.number_input(
            "Robust z threshold",
            min_value=0.5,
            max_value=20.0,
            value=3.5,
            step=0.5,
            disabled=method != "robust-z",
        )
        sigma = st.slider("Gaussian smoothing [cells]", 0.0, 3.0, 0.0, 0.25)
        minimum_cells = st.number_input("Minimum connected cells", 1, 500, 3)
        connectivity = st.selectbox("Cell connectivity", (8, 4))
        with st.expander("Morphological cleanup"):
            opening = st.number_input("Opening iterations", 0, 5, 0)
            closing = st.number_input("Closing iterations", 0, 5, 0)

        st.divider()
        st.header("Earthquakes")
        catalog_options = (
            ("Synthetic observations", "Upload CSV", "None")
            if source_mode == "Synthetic demonstration"
            else ("Upload CSV", "None")
        )
        catalog_mode = st.radio("Catalogue", catalog_options, index=0)
        if catalog_mode == "Synthetic observations":
            earthquakes = demo_earthquakes
            earthquake_source: dict[str, str | int] = {
                "source": "synthetic observations v1",
                "event_count": len(earthquakes),
            }
        elif catalog_mode == "Upload CSV":
            uploaded_catalog = st.file_uploader("Earthquake CSV", type="csv")
            if uploaded_catalog is None:
                earthquakes = pd.DataFrame(columns=["event_id", *REQUIRED_COLUMNS])
                earthquake_source = {"source": "none", "event_count": 0}
                st.caption("Waiting for a catalogue; the strain analysis remains available.")
            else:
                try:
                    earthquakes = _uploaded_catalog(uploaded_catalog)
                except (OSError, ValueError) as exc:
                    st.error(f"Could not read the earthquake catalogue: {exc}")
                    st.stop()
                earthquake_source = {
                    "source": "uploaded CSV",
                    **_upload_provenance(uploaded_catalog),
                    "event_count": len(earthquakes),
                    "discarded_rows": int(earthquakes.attrs.get("discarded_rows", 0)),
                }
        else:
            earthquakes = pd.DataFrame(columns=["event_id", *REQUIRED_COLUMNS])
            earthquake_source = {"source": "none", "event_count": 0}
        buffer_km = st.number_input("Association buffer [km]", 0.0, 1000.0, 50.0, 10.0)

    config = AnomalyConfig(
        variable=variable,
        method=method,
        percentile=percentile,
        robust_z_threshold=robust_z,
        gaussian_sigma_cells=sigma,
        minimum_cells=int(minimum_cells),
        opening_iterations=int(opening),
        closing_iterations=int(closing),
        connectivity=int(connectivity),
    )
    try:
        result = detect_anomalies(dataset, config)
        zones = candidate_zone_table(result, earthquakes, buffer_km=buffer_km)
    except (ValueError, RuntimeError) as exc:
        st.error(str(exc))
        st.stop()

    _header()
    st.warning(
        "Candidate regions are for expert investigation. Spatial coincidence does not demonstrate "
        "causality, and this interface does not provide earthquake forecasts or operational hazard "
        "assessments."
    )
    metric_columns = st.columns(3)
    metric_columns[0].metric("Candidate regions", len(result.regions))
    metric_columns[1].metric("Anomalous cells", int(np.count_nonzero(result.labels)))
    metric_columns[2].metric("Earthquakes shown", len(earthquakes))

    map_tab, zones_tab, sensitivity_tab, method_tab = st.tabs(
        ["Map", "Candidate zones", "Sensitivity", "Method & limits"]
    )
    with map_tab:
        st.plotly_chart(_map_figure(result, earthquakes), width="stretch", theme=None)
        color_min, color_max = _display_range(result)
        st.caption(
            f"Threshold: {result.threshold_value:.5g} {result.grid.units}. "
            f"Display range: {color_min:.5g}–{color_max:.5g} {result.grid.units} "
            "(finite minimum to 99.5th percentile). Transparent cells contain no data; "
            "outlines follow connected raster cells and marker size follows earthquake magnitude. "
            "Basemap: Esri World Imagery (no administrative overlay). Tectonic context: "
            "Bird (2003) PB2002 boundaries, GeoJSON by Hugo Ahlenius/Nordpil (ODC-By 1.0)."
        )
    with zones_tab:
        st.dataframe(zones, hide_index=True, width="stretch")
        st.download_button(
            "Download candidate zones CSV",
            zones.to_csv(index=False),
            "candidate_zones.csv",
            "text/csv",
        )
        st.download_button(
            "Download detected regions GeoJSON",
            json.dumps(regions_geojson(result), indent=2),
            "detected_regions.geojson",
            "application/geo+json",
        )
        metadata = {
            "experimental": True,
            "variable": result.grid.variable,
            "units": result.grid.units,
            "threshold_value": result.threshold_value,
            "parameters": asdict(config),
            "buffer_km": buffer_km,
            "candidate_zone_count": len(result.regions),
            "earthquake_count": len(earthquakes),
            "strain_source": strain_source,
            "earthquake_source": earthquake_source,
            "interpretation": "candidate regions for expert investigation; not a forecast",
        }
        st.download_button(
            "Download processing metadata",
            json.dumps(metadata, indent=2),
            "processing_metadata.json",
            "application/json",
        )
    with sensitivity_tab:
        if method == "percentile":
            summary = pd.DataFrame(
                sensitivity_summary(dataset, (90.0, 95.0, 97.5, 99.0), config=config)
            )
            st.plotly_chart(_sensitivity_figure(summary), width="stretch", theme=None)
            st.dataframe(summary, hide_index=True, width="stretch")
        else:
            st.info("Select the percentile method to compare the 90, 95, 97.5 and 99% thresholds.")
    with method_tab:
        st.markdown(
            """
            ### Numerical workflow

            The app reads the selected NetCDF variable, preserves geographic coordinates and NaNs,
            optionally smooths finite values, applies the configured transparent threshold, and
            labels connected raster cells. It never segments a rendered PNG.

            ### Interpretation boundary

            `tensor_magnitude` identifies total deformation concentration but does not preserve
            mechanism, sign, or orientation. Results inherit GNSS, interpolation, differentiation,
            grid-resolution, boundary, catalogue, and parameter uncertainty. Earthquake counts and
            distances are descriptive associations—not causal evidence or hazard probabilities.
            """
        )


if __name__ == "__main__":
    run()
