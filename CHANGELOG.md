# Changelog

All notable changes are documented here following semantic versioning.

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
