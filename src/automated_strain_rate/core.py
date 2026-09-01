"""Numerical strain-rate calculations on regular geographic grids."""

from __future__ import annotations

import numpy as np
import xarray as xr

EARTH_KM_PER_DEGREE = 111.195
SUPPORTED_VELOCITY_UNITS = {"mm/yr": 1.0, "m/yr": 1_000.0}


class GridValidationError(ValueError):
    """Raised when velocity-grid inputs cannot support strain estimation."""


def _coordinate(values: np.ndarray, name: str) -> np.ndarray:
    coordinate = np.asarray(values, dtype=float)
    if coordinate.ndim != 1 or coordinate.size < 2:
        raise GridValidationError(f"{name} must be a one-dimensional array with at least 2 values.")
    if not np.all(np.isfinite(coordinate)):
        raise GridValidationError(f"{name} must contain only finite values.")
    differences = np.diff(coordinate)
    if np.any(differences == 0) or not (np.all(differences > 0) or np.all(differences < 0)):
        raise GridValidationError(f"{name} must be strictly monotonic.")
    return coordinate


def _velocity(values: np.ndarray, shape: tuple[int, int], name: str) -> np.ndarray:
    velocity = np.asarray(values, dtype=float)
    if velocity.shape != shape:
        raise GridValidationError(f"{name} must have shape {shape}; received {velocity.shape}.")
    if not np.all(np.isfinite(velocity)):
        raise GridValidationError(f"{name} must contain only finite values.")
    return velocity


def strain_from_regular_grid(
    east_velocity: np.ndarray,
    north_velocity: np.ndarray,
    longitude: np.ndarray,
    latitude: np.ndarray,
    *,
    velocity_unit: str = "mm/yr",
) -> xr.Dataset:
    """Derive a 2-D infinitesimal strain-rate tensor from a regular lon/lat grid.

    Geographic coordinates are projected to a local equirectangular frame at the
    grid's mean latitude. Output components are in microstrain/year: numerically,
    one millimetre/year per kilometre equals one microstrain/year.
    """
    lon = _coordinate(longitude, "longitude")
    lat = _coordinate(latitude, "latitude")
    if np.any(np.abs(lat) > 90) or np.any(np.abs(lon) > 360):
        raise GridValidationError("Longitude or latitude is outside its physical range.")
    if velocity_unit not in SUPPORTED_VELOCITY_UNITS:
        supported = ", ".join(sorted(SUPPORTED_VELOCITY_UNITS))
        raise GridValidationError(f"velocity_unit must be one of: {supported}.")

    shape = (lat.size, lon.size)
    east = _velocity(east_velocity, shape, "east_velocity")
    north = _velocity(north_velocity, shape, "north_velocity")
    scale = SUPPORTED_VELOCITY_UNITS[velocity_unit]
    east_mm = east * scale
    north_mm = north * scale

    mean_latitude = float(np.mean(lat))
    x_km = lon * EARTH_KM_PER_DEGREE * np.cos(np.deg2rad(mean_latitude))
    y_km = lat * EARTH_KM_PER_DEGREE
    edge_order = 2 if min(shape) >= 3 else 1

    du_dx = np.gradient(east_mm, x_km, axis=1, edge_order=edge_order)
    du_dy = np.gradient(east_mm, y_km, axis=0, edge_order=edge_order)
    dv_dx = np.gradient(north_mm, x_km, axis=1, edge_order=edge_order)
    dv_dy = np.gradient(north_mm, y_km, axis=0, edge_order=edge_order)

    exx = du_dx
    eyy = dv_dy
    exy = 0.5 * (du_dy + dv_dx)
    rotation = 0.5 * (dv_dx - du_dy)
    dilatation = exx + eyy
    maximum_shear = np.sqrt(((exx - eyy) / 2.0) ** 2 + exy**2)
    principal_maximum = dilatation / 2.0 + maximum_shear
    principal_minimum = dilatation / 2.0 - maximum_shear
    tensor_magnitude = np.sqrt(exx**2 + eyy**2 + 2.0 * exy**2)

    coordinates = {"latitude": lat, "longitude": lon}
    dataset = xr.Dataset(
        data_vars={
            "east_velocity": (("latitude", "longitude"), east),
            "north_velocity": (("latitude", "longitude"), north),
            "exx": (("latitude", "longitude"), exx),
            "eyy": (("latitude", "longitude"), eyy),
            "exy": (("latitude", "longitude"), exy),
            "rotation": (("latitude", "longitude"), rotation),
            "dilatation": (("latitude", "longitude"), dilatation),
            "maximum_shear": (("latitude", "longitude"), maximum_shear),
            "principal_maximum": (("latitude", "longitude"), principal_maximum),
            "principal_minimum": (("latitude", "longitude"), principal_minimum),
            "tensor_magnitude": (("latitude", "longitude"), tensor_magnitude),
        },
        coords=coordinates,
        attrs={
            "method": "finite differences in a local equirectangular frame",
            "mean_latitude_degrees": mean_latitude,
            "earth_km_per_degree": EARTH_KM_PER_DEGREE,
            "input_velocity_unit": velocity_unit,
            "strain_rate_unit": "microstrain/yr",
        },
    )
    for variable in ("exx", "eyy", "exy", "dilatation", "maximum_shear"):
        dataset[variable].attrs["units"] = "microstrain/yr"
    for variable in ("principal_maximum", "principal_minimum", "tensor_magnitude"):
        dataset[variable].attrs["units"] = "microstrain/yr"
    dataset["rotation"].attrs["units"] = "microradian/yr"
    dataset["east_velocity"].attrs["units"] = velocity_unit
    dataset["north_velocity"].attrs["units"] = velocity_unit
    return dataset
