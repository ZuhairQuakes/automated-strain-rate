from __future__ import annotations

import numpy as np
import pytest

from automated_strain_rate import GridValidationError, strain_from_regular_grid
from automated_strain_rate.core import EARTH_KM_PER_DEGREE


def test_affine_velocity_field_recovers_known_tensor() -> None:
    longitude = np.linspace(95.0, 96.0, 6)
    latitude = np.linspace(18.0, 19.0, 7)
    mean_latitude = latitude.mean()
    x_km = longitude * EARTH_KM_PER_DEGREE * np.cos(np.deg2rad(mean_latitude))
    y_km = latitude * EARTH_KM_PER_DEGREE
    x, y = np.meshgrid(x_km, y_km)
    east = 2.0 * x + 4.0 * y
    north = 6.0 * x - 3.0 * y

    result = strain_from_regular_grid(east, north, longitude, latitude)

    assert np.allclose(result["exx"], 2.0)
    assert np.allclose(result["eyy"], -3.0)
    assert np.allclose(result["exy"], 5.0)
    assert np.allclose(result["rotation"], 1.0)
    assert np.allclose(result["dilatation"], -1.0)
    assert np.allclose(result["maximum_shear"], np.sqrt(31.25))


def test_metre_velocity_conversion() -> None:
    longitude = np.array([0.0, 0.5, 1.0])
    latitude = np.array([0.0, 0.5, 1.0])
    x_km = longitude * EARTH_KM_PER_DEGREE * np.cos(np.deg2rad(latitude.mean()))
    east_m = np.tile(x_km, (3, 1)) / 1_000.0
    north_m = np.zeros_like(east_m)

    result = strain_from_regular_grid(
        east_m,
        north_m,
        longitude,
        latitude,
        velocity_unit="m/yr",
    )

    assert np.allclose(result["exx"], 1.0)


def test_rejects_bad_grid() -> None:
    with pytest.raises(GridValidationError, match="strictly monotonic"):
        strain_from_regular_grid(
            np.zeros((2, 2)),
            np.zeros((2, 2)),
            np.array([1.0, 1.0]),
            np.array([1.0, 2.0]),
        )
