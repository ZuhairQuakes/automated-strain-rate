"""Create a deterministic two-anomaly field and fake earthquake catalogue."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_directory",
        nargs="?",
        type=Path,
        default=Path("outputs/synthetic-input"),
    )
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
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
    grid_path = args.output_directory / "strain-rate.nc"
    dataset.to_netcdf(grid_path)
    earthquakes = pd.DataFrame(
        {
            "event_id": ["synthetic-1", "synthetic-2", "synthetic-3", "synthetic-4"],
            "longitude": [96.02, 96.30, 97.21, 95.25],
            "latitude": [20.10, 20.35, 25.05, 27.20],
            "magnitude": [5.8, 4.9, 6.2, 4.5],
            "time": [
                "2024-01-10T00:00:00Z",
                "2024-03-18T00:00:00Z",
                "2024-06-22T00:00:00Z",
                "2024-09-04T00:00:00Z",
            ],
            "depth": [15.0, 24.0, 18.0, 30.0],
        }
    )
    catalogue_path = args.output_directory / "earthquakes.csv"
    earthquakes.to_csv(catalogue_path, index=False)
    print(f"Wrote {grid_path}")
    print(f"Wrote {catalogue_path}")


if __name__ == "__main__":
    main()
