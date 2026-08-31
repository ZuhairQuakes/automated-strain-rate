# Automated crustal strain-rate assessment from GNSS velocities

[![Repository quality](https://github.com/ZuhairQuakes/GNSS-Earthquake/actions/workflows/repository-quality.yml/badge.svg)](https://github.com/ZuhairQuakes/GNSS-Earthquake/actions/workflows/repository-quality.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A reproducible notebook workflow for interpolating sparse GNSS velocity observations and calculating continuous crustal strain-rate fields. The example data cover Myanmar and support a grid-resolution sensitivity analysis.

![Strain-rate comparison](images/mynamar.png)

## Method

1. Read east, north, and vertical station velocities with their uncertainties.
2. Call GMT `gpsgridder` to interpolate the horizontal velocity field.
3. Load the resulting NetCDF grids with xarray.
4. Calculate spatial velocity gradients and derived strain quantities, including maximum shear, dilatation, and the second invariant.
5. Repeat across grid intervals and compare the mapped results.

## Repository map

| Path | Purpose |
| --- | --- |
| [`nbtk/strain_rates_compute.ipynb`](nbtk/strain_rates_compute.ipynb) | complete interpolation and strain-rate workflow |
| [`data/mymr_vel_space_ITRF2014.txt`](data/mymr_vel_space_ITRF2014.txt) | tracked example GNSS velocity field |
| [`images/`](images/) | study-area, velocity, and result figures |
| [`environment.yml`](environment.yml) | Python, geospatial, NetCDF, Jupyter, and GMT environment |
| [`tools/validate_repository.py`](tools/validate_repository.py) | dependency-free structural validation |

## Reproduce the analysis

```bash
git clone https://github.com/ZuhairQuakes/GNSS-Earthquake.git
cd GNSS-Earthquake
conda env create -f environment.yml
conda activate gnss-earthquake
python tools/validate_repository.py
gmt --version
jupyter lab nbtk/strain_rates_compute.ipynb
```

Launch Jupyter from the repository root. The notebook reads `data/mymr_vel_space_ITRF2014.txt` using a repository-relative path and writes generated NetCDF grids to `Output_gpsgridder/`. Generated grids and GMT temporary files are ignored by Git.

## Input format

The whitespace-delimited example file is read with these columns:

```text
Lon Lat Ve Vn Vu Se Sn Su Name
```

Longitude and latitude are decimal degrees; velocity and uncertainty units must remain consistent throughout a run. For a new velocity field, document its reference frame, epoch, units, processing source, and station-selection criteria.

## Reproducibility notes

Record the Git commit, GMT version, grid interval, interpolation parameters, bounding box, and environment export with each result. Because spatial derivatives amplify interpolation choices, comparisons should use the same input stations and map extent.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for change and review expectations. This project is available under the [MIT License](LICENSE).
