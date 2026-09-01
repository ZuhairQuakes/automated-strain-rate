from __future__ import annotations

from pathlib import Path

import pytest

from automated_strain_rate.gmt import GMTConfig, gpsgridder_command


def test_gpsgridder_command_is_argument_vector() -> None:
    config = GMTConfig(94.5, 98.0, 16.0, 28.0, 0.3)

    command = gpsgridder_command(Path("stations.txt"), Path("out/velocity"), config)

    assert command[:3] == ["gmt", "gpsgridder", "stations.txt"]
    assert "-R94.5/98.0/16.0/28.0" in command
    assert "-I0.3" in command
    assert command[-1] == "-Gout/velocity_%s.nc"


def test_gmt_config_rejects_invalid_region() -> None:
    with pytest.raises(ValueError, match="west < east"):
        GMTConfig(98.0, 94.5, 16.0, 28.0, 0.3).validate()
