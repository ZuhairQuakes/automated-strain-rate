from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

from automated_strain_rate.io import load_gmt_grid, read_velocity_catalog


def test_read_velocity_catalog(tmp_path: Path) -> None:
    source = tmp_path / "stations.txt"
    source.write_text(
        "# Lon Lat Ve Vn Vu Se Sn Su Name\n"
        "95 18 10 20 0 1 1 1 A\n"
        "96 19 11 21 0 1 1 1 B\n"
        "97 20 12 22 0 1 1 1 C\n",
        encoding="utf-8",
    )

    catalog = read_velocity_catalog(source)

    assert catalog["Name"].tolist() == ["A", "B", "C"]
    assert catalog["Ve"].tolist() == [10, 11, 12]


def test_load_gmt_grid_normalizes_dimension_order(tmp_path: Path) -> None:
    source = tmp_path / "grid.nc"
    dataset = xr.Dataset(
        {"z": (("y", "x"), np.arange(6).reshape(2, 3))},
        coords={"x": [95.0, 96.0, 97.0], "y": [18.0, 19.0]},
    )
    dataset.to_netcdf(source)

    values, longitude, latitude = load_gmt_grid(source)

    assert values.shape == (2, 3)
    assert longitude.tolist() == [95.0, 96.0, 97.0]
    assert latitude.tolist() == [18.0, 19.0]
