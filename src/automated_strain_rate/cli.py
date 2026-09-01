"""Command-line tools for reproducible GNSS strain-rate estimation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from automated_strain_rate import __version__, read_velocity_catalog, strain_from_regular_grid
from automated_strain_rate.gmt import GMTConfig, run_gmt_pipeline
from automated_strain_rate.io import load_gmt_grid


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="strain-rate", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser("inspect", help="Validate and summarize a GNSS velocity file")
    inspect.add_argument("catalog", type=Path)

    derive = commands.add_parser("derive", help="Derive strain from existing GMT velocity grids")
    derive.add_argument("east_grid", type=Path)
    derive.add_argument("north_grid", type=Path)
    derive.add_argument("output", type=Path)
    derive.add_argument("--variable", default="z")
    derive.add_argument("--velocity-unit", choices=("mm/yr", "m/yr"), default="mm/yr")

    compute = commands.add_parser("compute", help="Run GMT interpolation and strain derivation")
    compute.add_argument("catalog", type=Path)
    compute.add_argument("output_directory", type=Path)
    compute.add_argument(
        "--region",
        nargs=4,
        type=float,
        metavar=("WEST", "EAST", "SOUTH", "NORTH"),
        required=True,
    )
    compute.add_argument("--spacing", type=float, required=True, help="Grid spacing in degrees")
    compute.add_argument("--poisson", type=float, default=0.5)
    compute.add_argument("--fudge-factor", type=float, default=0.01)
    compute.add_argument("--eigenvalue-cutoff", type=float, default=0.0001)
    compute.add_argument("--velocity-unit", choices=("mm/yr", "m/yr"), default="mm/yr")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        catalog = read_velocity_catalog(args.catalog)
        summary = {
            "stations": len(catalog),
            "longitude_range": [float(catalog["Lon"].min()), float(catalog["Lon"].max())],
            "latitude_range": [float(catalog["Lat"].min()), float(catalog["Lat"].max())],
        }
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "derive":
        east, longitude, latitude = load_gmt_grid(args.east_grid, args.variable)
        north, north_longitude, north_latitude = load_gmt_grid(args.north_grid, args.variable)
        if not (
            longitude.shape == north_longitude.shape
            and latitude.shape == north_latitude.shape
            and np.allclose(longitude, north_longitude)
            and np.allclose(latitude, north_latitude)
        ):
            raise ValueError("East and north grids must use identical coordinates.")
        result = strain_from_regular_grid(
            east,
            north,
            longitude,
            latitude,
            velocity_unit=args.velocity_unit,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result.to_netcdf(args.output)
        destination = args.output
    else:
        west, east, south, north = args.region
        config = GMTConfig(
            west=west,
            east=east,
            south=south,
            north=north,
            spacing_degrees=args.spacing,
            poisson=args.poisson,
            fudge_factor=args.fudge_factor,
            eigenvalue_cutoff=args.eigenvalue_cutoff,
        )
        destination = run_gmt_pipeline(
            args.catalog,
            args.output_directory,
            config,
            velocity_unit=args.velocity_unit,
        )
    print(f"Wrote {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
