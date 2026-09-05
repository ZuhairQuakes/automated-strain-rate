"""Deterministic demonstration data for documentation and interface testing."""

from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr


def synthetic_investigation_data() -> tuple[xr.Dataset, pd.DataFrame]:
    """Return a two-anomaly strain field and four fictional earthquake observations."""
    longitude = np.linspace(95.0, 98.0, 80)
    latitude = np.linspace(16.0, 28.0, 120)
    lon, lat = np.meshgrid(longitude, latitude)
    broad = 0.060 * np.exp(-(((lon - 96.0) / 0.22) ** 2 + ((lat - 20.0) / 0.75) ** 2))
    compact = 0.045 * np.exp(-(((lon - 97.2) / 0.12) ** 2 + ((lat - 25.0) / 0.45) ** 2))
    background = 0.002 + 0.0004 * np.sin(lon * 4.0) * np.cos(lat * 1.5)
    magnitude = background + broad + compact
    magnitude[:4, :5] = np.nan
    dataset = xr.Dataset(
        {"tensor_magnitude": (("latitude", "longitude"), magnitude)},
        coords={"longitude": longitude, "latitude": latitude},
        attrs={
            "strain_rate_unit": "microstrain/yr",
            "provenance": "deterministic synthetic validation field; not an observation",
        },
    )
    dataset["tensor_magnitude"].attrs["units"] = "microstrain/yr"
    earthquakes = pd.DataFrame(
        {
            "event_id": ["synthetic-1", "synthetic-2", "synthetic-3", "synthetic-4"],
            "longitude": [96.02, 96.30, 97.21, 95.25],
            "latitude": [20.10, 20.35, 25.05, 27.20],
            "magnitude": [5.8, 4.9, 6.2, 4.5],
            "time": pd.to_datetime(
                ["2024-01-10", "2024-03-18", "2024-06-22", "2024-09-04"], utc=True
            ),
            "depth": [15.0, 24.0, 18.0, 30.0],
        }
    )
    return dataset, earthquakes
