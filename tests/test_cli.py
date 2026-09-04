from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import xarray as xr

from automated_strain_rate.cli import main


def test_inspect_command(tmp_path: Path, capsys) -> None:
    source = tmp_path / "stations.txt"
    source.write_text(
        "95 18 10 20 0 1 1 1 A\n96 19 11 21 0 1 1 1 B\n97 20 12 22 0 1 1 1 C\n",
        encoding="utf-8",
    )

    assert main(["inspect", str(source)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["stations"] == 3


def test_investigate_command_writes_all_outputs(tmp_path: Path, capsys) -> None:
    values = np.zeros((10, 10))
    values[3:6, 3:6] = 10.0
    grid = tmp_path / "strain-rate.nc"
    xr.Dataset(
        {"tensor_magnitude": (("latitude", "longitude"), values)},
        coords={"longitude": np.linspace(95, 96, 10), "latitude": np.linspace(18, 19, 10)},
        attrs={"strain_rate_unit": "microstrain/yr"},
    ).to_netcdf(grid)
    earthquakes = tmp_path / "earthquakes.csv"
    earthquakes.write_text(
        "longitude,latitude,magnitude,time,depth\n95.45,18.45,5.2,2025-01-01T00:00:00Z,12\n",
        encoding="utf-8",
    )
    output = tmp_path / "investigation"

    assert (
        main(
            [
                "investigate",
                str(grid),
                str(output),
                "--percentile",
                "90",
                "--minimum-cells",
                "1",
                "--earthquakes",
                str(earthquakes),
                "--sensitivity-percentiles",
                "80",
                "90",
                "95",
            ]
        )
        == 0
    )

    assert "not forecasts" in capsys.readouterr().out
    expected = {
        "candidate_zones.csv",
        "detected_regions.geojson",
        "investigation_map.png",
        "processing_metadata.json",
        "sensitivity_summary.csv",
        "strain_vs_earthquakes.png",
    }
    assert expected <= {path.name for path in output.iterdir()}
    metadata = json.loads((output / "processing_metadata.json").read_text(encoding="utf-8"))
    assert metadata["interpretation"].endswith("not a forecast")
