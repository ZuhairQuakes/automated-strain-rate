# Automated Strain Rate

[![Quality](https://github.com/ZuhairQuakes/automated-strain-rate/actions/workflows/repository-quality.yml/badge.svg)](https://github.com/ZuhairQuakes/automated-strain-rate/actions/workflows/repository-quality.yml)
[![MIT licence](https://img.shields.io/badge/licence-MIT-2ea44f.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab.svg)](https://www.python.org/downloads/)

An open-source Python toolkit for turning horizontal GNSS velocities into
reproducible two-dimensional crustal strain-rate fields. The tested numerical
core derives strain tensors from regular velocity grids; an optional GMT
`gpsgridder` pipeline automates interpolation from station observations.

![Myanmar grid-resolution comparison](images/mynamar.png)

## Capabilities

- Validate whitespace-delimited GNSS velocity catalogues.
- Interpolate east and north velocities with GMT `gpsgridder` using a safe,
  recorded argument vector.
- Derive normal strain, tensor shear, rotation, dilatation, principal strain
  rates, maximum shear, and tensor magnitude.
- Write analysis-ready NetCDF with coordinates, units, method, and interpolation
  parameters in the metadata.
- Test the numerical implementation against an affine velocity field with a
  known analytical strain tensor.
- Inspect data or derive strain from existing GMT grids without rerunning the
  interpolation.

Read [`SCIENTIFIC_METHOD.md`](SCIENTIFIC_METHOD.md) before interpreting results.
This is research software, not an operational hazard assessment.

## Experimental: strain anomaly + earthquake explorer

An isolated research module now detects coherent high-`tensor_magnitude`
regions directly from the numerical NetCDF field, overlays a validated local or
cached USGS earthquake catalogue, and produces **candidate regions for expert
investigation**. It does not modify the validated strain-rate calculation.

```bash
python -m pip install -e ".[investigation]"
strain-rate investigate outputs/grid-03/strain-rate.nc outputs/investigation \
  --variable tensor_magnitude \
  --percentile 95 \
  --earthquakes earthquakes.csv \
  --buffer-km 50 \
  --sensitivity-percentiles 90 95 97.5 99
```

The command writes a candidate-zone CSV, raster-footprint GeoJSON, map,
diagnostic plot, processing metadata, and sensitivity summary. Read the complete
method, assumptions, USGS option, output schema, validation, and limitations in
[`EXPERIMENTAL_ANOMALY_EXPLORER.md`](EXPERIMENTAL_ANOMALY_EXPLORER.md).

A deterministic demonstration is included:

```bash
python examples/create_synthetic_investigation.py
strain-rate investigate outputs/synthetic-input/strain-rate.nc \
  outputs/synthetic-investigation \
  --earthquakes outputs/synthetic-input/earthquakes.csv
```

**Spatial coincidence between high strain rate and earthquakes does not
demonstrate causality and this tool does not provide earthquake forecasts or
operational hazard assessments.**

## Install

```bash
git clone https://github.com/ZuhairQuakes/automated-strain-rate.git
cd automated-strain-rate
python -m venv .venv
source .venv/bin/activate
python -m pip install .
```

Python 3.10 or newer is required. GMT is only required for the end-to-end
interpolation command. Install the complete Conda environment with:

```bash
conda env create -f environment.yml
conda activate automated-strain-rate
```

## Command line

Validate and summarize the bundled station field:

```bash
strain-rate inspect data/mymr_vel_space_ITRF2014.txt
```

Run GMT interpolation and derive a NetCDF strain-rate field:

```bash
strain-rate compute data/mymr_vel_space_ITRF2014.txt outputs/grid-03 \
  --region 94.5 98 16 28 \
  --spacing 0.3 \
  --poisson 0.5 \
  --fudge-factor 0.01 \
  --eigenvalue-cutoff 0.0001
```

Derive strain from existing GMT grids without invoking GMT:

```bash
strain-rate derive velocity_u.nc velocity_v.nc strain-rate.nc
```

Use `strain-rate --help` for all options.

## Python API

```python
import numpy as np
from automated_strain_rate import strain_from_regular_grid

longitude = np.linspace(95, 98, 31)
latitude = np.linspace(16, 28, 121)
east_velocity = np.zeros((latitude.size, longitude.size))  # mm/yr
north_velocity = np.zeros_like(east_velocity)

strain = strain_from_regular_grid(
    east_velocity,
    north_velocity,
    longitude,
    latitude,
    velocity_unit="mm/yr",
)
strain.to_netcdf("strain-rate.nc")
```

## Input format

The station reader expects:

```text
Lon Lat Ve Vn Vu Se Sn Su Name
```

Longitude and latitude are decimal degrees. Velocity units are selected by the
caller and must be consistent. Record reference frame, epoch, processing
source, uncertainty convention, station selection, and data licence for every
study. See [`data/Readme.md`](data/Readme.md).

## Repository map

| Path | Purpose |
| --- | --- |
| [`src/automated_strain_rate/`](src/automated_strain_rate/) | tested core plus isolated experimental anomaly and association modules |
| [`tests/`](tests/) | analytical, I/O, GMT-command, and CLI tests |
| [`nbtk/strain_rates_compute.ipynb`](nbtk/strain_rates_compute.ipynb) | historical exploratory workflow |
| [`SCIENTIFIC_METHOD.md`](SCIENTIFIC_METHOD.md) | equations, conventions, assumptions, and limitations |
| [`EXPERIMENTAL_ANOMALY_EXPLORER.md`](EXPERIMENTAL_ANOMALY_EXPLORER.md) | anomaly method, earthquake association, validation, and limitations |
| [`data/`](data/) | example station velocity field and provenance guidance |
| [`environment.yml`](environment.yml) | full Python, notebook, NetCDF, mapping, and GMT environment |

## Contribute

```bash
python -m pip install -e ".[dev,notebook]"
ruff check .
pytest
python tools/validate_repository.py
python -m build
```

Scientific contributions are welcome. Read [`CONTRIBUTING.md`](CONTRIBUTING.md),
follow the [Code of Conduct](CODE_OF_CONDUCT.md), and report security issues via
[`SECURITY.md`](SECURITY.md). Software is licensed under the [MIT License](LICENSE);
research users can cite the project with [`CITATION.cff`](CITATION.cff).
