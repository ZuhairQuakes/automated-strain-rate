"""Input and NetCDF helpers for GNSS velocity and strain-rate data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

CATALOG_COLUMNS = ("Lon", "Lat", "Ve", "Vn", "Vu", "Se", "Sn", "Su", "Name")


def read_velocity_catalog(path: str | Path) -> pd.DataFrame:
    """Read and validate the project's whitespace-delimited GNSS velocity format."""
    source = Path(path)
    catalog = pd.read_csv(
        source,
        sep=r"\s+",
        comment="#",
        header=None,
        names=CATALOG_COLUMNS,
        dtype={"Name": "string"},
    )
    for column in CATALOG_COLUMNS[:-1]:
        catalog[column] = pd.to_numeric(catalog[column], errors="coerce")
    catalog = catalog.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["Lon", "Lat", "Ve", "Vn", "Name"]
    )
    catalog = catalog.loc[
        catalog["Lon"].between(-180, 360, inclusive="both")
        & catalog["Lat"].between(-90, 90, inclusive="both")
    ].reset_index(drop=True)
    if len(catalog) < 3:
        raise ValueError("At least three valid GNSS stations are required.")
    return catalog


def load_gmt_grid(
    path: str | Path,
    variable: str = "z",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load a two-dimensional GMT NetCDF grid as values, longitude, and latitude."""
    with xr.open_dataset(path) as dataset:
        if variable not in dataset:
            raise ValueError(f"Variable {variable!r} is not present in {path}.")
        data = dataset[variable]
        longitude_name = next(
            (name for name in ("longitude", "lon", "x") if name in data.coords), None
        )
        latitude_name = next(
            (name for name in ("latitude", "lat", "y") if name in data.coords), None
        )
        if longitude_name is None or latitude_name is None:
            raise ValueError(f"Could not identify longitude and latitude coordinates in {path}.")
        ordered = data.transpose(latitude_name, longitude_name)
        values = ordered.to_numpy().copy()
        longitude = ordered[longitude_name].to_numpy().copy()
        latitude = ordered[latitude_name].to_numpy().copy()
    return values, longitude, latitude
