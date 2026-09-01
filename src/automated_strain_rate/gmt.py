"""Safe orchestration of GMT gpsgridder for GNSS velocity interpolation."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

import numpy as np

from automated_strain_rate.core import strain_from_regular_grid
from automated_strain_rate.io import load_gmt_grid, read_velocity_catalog


@dataclass(frozen=True)
class GMTConfig:
    """Configuration for a GMT gpsgridder interpolation."""

    west: float
    east: float
    south: float
    north: float
    spacing_degrees: float
    poisson: float = 0.5
    fudge_factor: float = 0.01
    eigenvalue_cutoff: float = 0.0001

    def validate(self) -> None:
        numeric_values = (
            self.west,
            self.east,
            self.south,
            self.north,
            self.spacing_degrees,
            self.poisson,
            self.fudge_factor,
            self.eigenvalue_cutoff,
        )
        if not all(isfinite(value) for value in numeric_values):
            raise ValueError("All GMT configuration values must be finite.")
        if not self.west < self.east or not self.south < self.north:
            raise ValueError("Region bounds must satisfy west < east and south < north.")
        if not 0 < self.spacing_degrees:
            raise ValueError("spacing_degrees must be greater than zero.")
        if not -1 < self.poisson <= 0.5:
            raise ValueError("poisson must be greater than -1 and no more than 0.5.")
        if self.fudge_factor < 0 or self.eigenvalue_cutoff < 0:
            raise ValueError("fudge_factor and eigenvalue_cutoff cannot be negative.")


def gpsgridder_command(input_path: Path, output_base: Path, config: GMTConfig) -> list[str]:
    """Build the argument vector used to invoke GMT without a shell."""
    config.validate()
    region = f"{config.west}/{config.east}/{config.south}/{config.north}"
    return [
        "gmt",
        "gpsgridder",
        str(input_path),
        f"-R{region}",
        f"-I{config.spacing_degrees}",
        f"-S{config.poisson}",
        f"-Fd{config.fudge_factor}",
        f"-C{config.eigenvalue_cutoff}",
        "-fg",
        "-r",
        f"-G{output_base}_%s.nc",
    ]


def run_gmt_pipeline(
    catalog_path: str | Path,
    output_directory: str | Path,
    config: GMTConfig,
    *,
    velocity_unit: str = "mm/yr",
) -> Path:
    """Interpolate GNSS velocities with GMT and write a strain-rate NetCDF dataset."""
    if shutil.which("gmt") is None:
        raise RuntimeError("GMT is required for interpolation but was not found on PATH.")
    output_dir = Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    stations = read_velocity_catalog(catalog_path)
    interpolation_input = output_dir / "gpsgridder-input.txt"
    output_base = output_dir / "velocity"
    stations.loc[:, ["Lon", "Lat", "Ve", "Vn"]].to_csv(
        interpolation_input,
        sep=" ",
        header=False,
        index=False,
    )
    try:
        subprocess.run(
            gpsgridder_command(interpolation_input, output_base, config),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(f"GMT gpsgridder failed: {message}") from exc
    finally:
        interpolation_input.unlink(missing_ok=True)

    east, longitude, latitude = load_gmt_grid(output_dir / "velocity_u.nc")
    north, north_lon, north_lat = load_gmt_grid(output_dir / "velocity_v.nc")
    compatible_coordinates = (
        longitude.shape == north_lon.shape
        and latitude.shape == north_lat.shape
        and np.allclose(longitude, north_lon)
        and np.allclose(latitude, north_lat)
    )
    if not compatible_coordinates:
        raise RuntimeError("GMT east and north grids have incompatible coordinates.")
    result = strain_from_regular_grid(
        east,
        north,
        longitude,
        latitude,
        velocity_unit=velocity_unit,
    )
    result.attrs.update(
        {
            "interpolation": "GMT gpsgridder",
            "station_count": len(stations),
            "poisson_ratio": config.poisson,
            "fudge_factor": config.fudge_factor,
            "eigenvalue_cutoff": config.eigenvalue_cutoff,
        }
    )
    destination = output_dir / "strain-rate.nc"
    result.to_netcdf(destination)
    return destination
