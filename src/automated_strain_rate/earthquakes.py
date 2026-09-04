"""Validated earthquake catalogues from CSV files or the USGS FDSN service."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd

USGS_ENDPOINT = "https://earthquake.usgs.gov/fdsnws/event/1/query"
REQUIRED_COLUMNS = ("longitude", "latitude", "magnitude", "time", "depth")
_ALIASES = {
    "longitude": ("longitude", "lon"),
    "latitude": ("latitude", "lat"),
    "magnitude": ("magnitude", "mag"),
    "depth": ("depth",),
    "time": ("time", "datetime", "origin_time"),
    "event_id": ("event_id", "eventid", "id"),
}


def _find_column(frame: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    lookup = {str(column).strip().casefold(): str(column) for column in frame.columns}
    return next((lookup[alias] for alias in aliases if alias in lookup), None)


def normalize_earthquake_catalog(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize required fields and report discarded malformed rows in attrs."""
    selected: dict[str, pd.Series] = {}
    for canonical in ("longitude", "latitude", "magnitude", "depth"):
        source = _find_column(frame, _ALIASES[canonical])
        if source is None:
            raise ValueError(f"Earthquake catalogue is missing {canonical!r}.")
        selected[canonical] = pd.to_numeric(frame[source], errors="coerce")

    time_source = _find_column(frame, _ALIASES["time"])
    if time_source is None:
        raise ValueError("Earthquake catalogue is missing 'time'.")
    date_source = _find_column(frame, ("date",))
    if date_source is not None and str(time_source).strip().casefold() == "time":
        combined = frame[date_source].astype("string") + " " + frame[time_source].astype("string")
        selected["time"] = pd.to_datetime(combined, errors="coerce", utc=True, dayfirst=True)
    else:
        selected["time"] = pd.to_datetime(frame[time_source], errors="coerce", utc=True)

    event_source = _find_column(frame, _ALIASES["event_id"])
    if event_source is not None:
        selected["event_id"] = frame[event_source].astype("string")
    else:
        selected["event_id"] = pd.Series(
            [f"event-{index + 1}" for index in range(len(frame))], index=frame.index, dtype="string"
        )

    catalog = pd.DataFrame(selected)
    numeric = catalog[["longitude", "latitude", "magnitude", "depth"]].to_numpy(float)
    valid = np.all(np.isfinite(numeric), axis=1)
    valid &= catalog["longitude"].between(-180, 360, inclusive="both").to_numpy()
    valid &= catalog["latitude"].between(-90, 90, inclusive="both").to_numpy()
    valid &= catalog["time"].notna().to_numpy()
    normalized = catalog.loc[valid, ["event_id", *REQUIRED_COLUMNS]].reset_index(drop=True)
    normalized.attrs["source_rows"] = int(len(frame))
    normalized.attrs["discarded_rows"] = int(len(frame) - len(normalized))
    if normalized.empty:
        raise ValueError("Earthquake catalogue contains no valid observations.")
    return normalized


def read_earthquake_catalog(path: str | Path) -> pd.DataFrame:
    """Read a CSV catalogue with standard or common case-insensitive column names."""
    return normalize_earthquake_catalog(pd.read_csv(path, skipinitialspace=True))


def catalog_from_usgs_geojson(payload: Mapping[str, Any]) -> pd.DataFrame:
    """Validate and normalize an earthquake GeoJSON response."""
    if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
        raise ValueError("USGS response is not a GeoJSON FeatureCollection.")
    rows = []
    for feature in payload["features"]:
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        properties = feature.get("properties") or {}
        if len(coordinates) < 3:
            continue
        milliseconds = properties.get("time")
        timestamp = (
            datetime.fromtimestamp(milliseconds / 1000.0, tz=UTC).isoformat()
            if isinstance(milliseconds, int | float)
            else None
        )
        rows.append(
            {
                "event_id": feature.get("id"),
                "longitude": coordinates[0],
                "latitude": coordinates[1],
                "depth": coordinates[2],
                "magnitude": properties.get("mag"),
                "time": timestamp,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["event_id", *REQUIRED_COLUMNS])
    return normalize_earthquake_catalog(pd.DataFrame(rows))


def _download_json(url: str, timeout: float) -> dict[str, Any]:
    with urlopen(url, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS endpoint
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("USGS response must be a JSON object.")
    return payload


def query_usgs_catalog(
    *,
    bounds: tuple[float, float, float, float],
    start_time: str,
    end_time: str,
    minimum_magnitude: float,
    cache_path: str | Path | None = None,
    timeout: float = 30.0,
    downloader: Callable[[str, float], dict[str, Any]] = _download_json,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Query USGS within west/east/south/north bounds, with reproducible caching."""
    west, east, south, north = bounds
    if not west < east or not south < north:
        raise ValueError("USGS bounds must satisfy west < east and south < north.")
    if not np.isfinite(minimum_magnitude):
        raise ValueError("minimum_magnitude must be finite.")
    parameters: dict[str, str | float] = {
        "format": "geojson",
        "starttime": start_time,
        "endtime": end_time,
        "minmagnitude": float(minimum_magnitude),
        "minlongitude": float(west),
        "maxlongitude": float(east),
        "minlatitude": float(south),
        "maxlatitude": float(north),
        "orderby": "time-asc",
        "eventtype": "earthquake",
    }
    cache = Path(cache_path) if cache_path is not None else None
    payload: dict[str, Any]
    cache_used = False
    if cache is not None and cache.exists():
        saved = json.loads(cache.read_text(encoding="utf-8"))
        if saved.get("query") == parameters and isinstance(saved.get("response"), dict):
            payload = saved["response"]
            cache_used = True
        else:
            payload = downloader(f"{USGS_ENDPOINT}?{urlencode(parameters)}", timeout)
    else:
        payload = downloader(f"{USGS_ENDPOINT}?{urlencode(parameters)}", timeout)
    if cache is not None and not cache_used:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps(
                {
                    "query": parameters,
                    "downloaded_at": datetime.now(UTC).isoformat(),
                    "response": payload,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    catalog = catalog_from_usgs_geojson(payload)
    metadata = {
        "source": "USGS FDSN",
        "endpoint": USGS_ENDPOINT,
        "query": parameters,
        "cache_path": str(cache) if cache is not None else None,
        "cache_used": cache_used,
        "event_count": len(catalog),
    }
    return catalog, metadata
