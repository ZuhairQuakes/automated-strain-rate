"""Reproducible strain-rate estimation from horizontal GNSS velocities."""

from automated_strain_rate.core import GridValidationError, strain_from_regular_grid
from automated_strain_rate.io import read_velocity_catalog

__all__ = ["GridValidationError", "read_velocity_catalog", "strain_from_regular_grid"]
__version__ = "0.3.0"
