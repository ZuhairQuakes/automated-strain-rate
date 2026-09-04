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

    investigate = commands.add_parser(
        "investigate",
        help="EXPERIMENTAL: detect strain anomalies and compare them with earthquakes",
    )
    investigate.add_argument("strain_grid", type=Path)
    investigate.add_argument("output_directory", type=Path)
    investigate.add_argument("--variable", default="tensor_magnitude")
    investigate.add_argument("--method", choices=("percentile", "robust-z"), default="percentile")
    investigate.add_argument("--percentile", type=float, default=95.0)
    investigate.add_argument("--robust-z-threshold", type=float, default=3.5)
    investigate.add_argument("--gaussian-sigma-cells", type=float, default=0.0)
    investigate.add_argument("--minimum-cells", type=int, default=3)
    investigate.add_argument("--opening-iterations", type=int, default=0)
    investigate.add_argument("--closing-iterations", type=int, default=0)
    investigate.add_argument("--connectivity", type=int, choices=(4, 8), default=8)
    investigate.add_argument("--earthquakes", type=Path, help="CSV earthquake catalogue")
    investigate.add_argument("--usgs-start", help="USGS query start time (ISO 8601)")
    investigate.add_argument("--usgs-end", help="USGS query end time (ISO 8601)")
    investigate.add_argument("--minimum-magnitude", type=float, default=4.5)
    investigate.add_argument("--buffer-km", type=float, default=50.0)
    investigate.add_argument(
        "--sensitivity-percentiles",
        nargs="+",
        type=float,
        default=(90.0, 95.0, 97.5, 99.0),
    )
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

    if args.command == "investigate":
        import pandas as pd

        from automated_strain_rate.anomaly import (
            AnomalyConfig,
            detect_anomalies,
            geographic_bounds,
            sensitivity_summary,
        )
        from automated_strain_rate.candidate_zones import write_investigation_outputs
        from automated_strain_rate.earthquakes import (
            REQUIRED_COLUMNS,
            query_usgs_catalog,
            read_earthquake_catalog,
        )

        if args.earthquakes is not None and (args.usgs_start or args.usgs_end):
            raise ValueError("Choose either --earthquakes or a USGS date range, not both.")
        if bool(args.usgs_start) != bool(args.usgs_end):
            raise ValueError("--usgs-start and --usgs-end must be supplied together.")
        config = AnomalyConfig(
            variable=args.variable,
            method=args.method,
            percentile=args.percentile,
            robust_z_threshold=args.robust_z_threshold,
            gaussian_sigma_cells=args.gaussian_sigma_cells,
            minimum_cells=args.minimum_cells,
            opening_iterations=args.opening_iterations,
            closing_iterations=args.closing_iterations,
            connectivity=args.connectivity,
        )
        result = detect_anomalies(args.strain_grid, config)
        if args.earthquakes is not None:
            earthquakes = read_earthquake_catalog(args.earthquakes)
            earthquake_metadata = {
                "source": "CSV",
                "path": str(args.earthquakes),
                "source_rows": earthquakes.attrs.get("source_rows"),
                "discarded_rows": earthquakes.attrs.get("discarded_rows"),
                "event_count": len(earthquakes),
            }
        elif args.usgs_start and args.usgs_end:
            earthquakes, earthquake_metadata = query_usgs_catalog(
                bounds=geographic_bounds(result.grid),
                start_time=args.usgs_start,
                end_time=args.usgs_end,
                minimum_magnitude=args.minimum_magnitude,
                cache_path=args.output_directory / "usgs_query.json",
            )
        else:
            earthquakes = pd.DataFrame(columns=["event_id", *REQUIRED_COLUMNS])
            earthquake_metadata = {"source": "none", "event_count": 0}
        if args.method == "percentile":
            sensitivity = pd.DataFrame(
                sensitivity_summary(
                    args.strain_grid,
                    tuple(args.sensitivity_percentiles),
                    config=config,
                )
            )
        else:
            sensitivity = pd.DataFrame(
                [
                    {
                        "method": "robust-z",
                        "robust_z_threshold": args.robust_z_threshold,
                        "zone_count": len(result.regions),
                        "anomalous_cell_count": int(np.count_nonzero(result.labels)),
                    }
                ]
            )
        outputs = write_investigation_outputs(
            result,
            earthquakes,
            sensitivity,
            args.output_directory,
            input_netcdf=args.strain_grid,
            earthquake_metadata=earthquake_metadata,
            buffer_km=args.buffer_km,
        )
        print("EXPERIMENTAL output: candidate regions for expert investigation; not forecasts.")
        for name, path in vars(outputs).items():
            print(f"{name}: {path}")
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
