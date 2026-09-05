# Changelog

All notable changes are documented here following semantic versioning.

## [0.3.0] - 2026-09-05

### Added

- Lightweight Streamlit explorer backed directly by the tested numerical
  anomaly and earthquake-association modules.
- Interactive NetCDF and earthquake-CSV upload, anomaly controls, candidate
  maps and tables, sensitivity visualization, and downloadable CSV/GeoJSON
  metadata.
- Built-in deterministic demonstration, application smoke test, Streamlit Cloud
  requirements, and container deployment.
- Projected CARTO basemap, georeferenced transparent strain field, explicit
  robust colour limits, earthquake date/magnitude labels, and separate zone
  symbology.
- Unlabelled Esri World Imagery replaces the administrative basemap, with a
  cited Bird (2003) PB2002 plate-boundary overlay for tectonic context.

### Scientific scope

- The interface remains an exploratory expert-review tool and never calculates
  a hazard probability or segments a rendered strain map.

## [0.2.0] - 2026-09-04

### Added

- Experimental numerical strain-anomaly segmentation using percentile or robust
  median/MAD thresholds and configurable morphology.
- Candidate-region statistics, raster-footprint GeoJSON, and transparent
  maximum-strain ranking.
- Validated local earthquake catalogues and reproducibly cached USGS queries.
- WGS84 geodesic earthquake association, static maps, diagnostics, and
  multi-threshold sensitivity summaries.
- Synthetic and mocked validation for anomaly, boundary, NaN, earthquake,
  distance, cache, sensitivity, and CLI-output behavior.

### Scientific scope

- Outputs are candidate regions for expert investigation, not forecasts or
  operational hazard assessments.

## [0.1.0] - 2026-09-01

### Added

- Installable `automated-strain-rate` Python package and `strain-rate` CLI.
- Tested regular-grid strain tensor calculation and GMT `gpsgridder` adapter.
- NetCDF outputs with units and reproducibility metadata.
- Analytical, I/O, GMT-command, and CLI tests.
- Scientific method, citation, community, security, and release documentation.
