# Experimental: strain anomaly + earthquake explorer

## Research question

Can a transparent spatial-segmentation method identify unusual concentrations
in a numerical strain-rate field, and how do those regions spatially coincide
with an observed earthquake catalogue?

The outputs are **candidate regions for expert investigation**. They are not
earthquake forecasts, hazard probabilities, warnings, or evidence of a causal
relationship.

## Why `tensor_magnitude` is the MVP variable

The first experiment uses the existing NetCDF variable `tensor_magnitude`,

```text
sqrt(exx² + eyy² + 2 exy²)
```

in `microstrain/yr`. This non-negative tensor norm identifies concentrated 2-D
deformation without cancellation between extension and contraction. It is more
suitable for a first general anomaly experiment than signed dilatation or one
principal component.

It does not identify the deformation mechanism, sign, or orientation. Because
it is derived from spatial velocity gradients, it can be elevated by GNSS
noise, interpolation choices, station geometry, grid boundaries, and smoothing.
Any candidate region must therefore be inspected alongside `exx`, `eyy`, `exy`,
principal strain rates, station coverage, and uncertainty.

## Method

The implementation operates on the numerical NetCDF field—not a rendered map:

```text
NetCDF strain values
→ coordinate and NaN validation
→ optional NaN-aware Gaussian smoothing
→ percentile or robust median/MAD threshold
→ optional binary opening/closing
→ connected raster components
→ geographic region statistics and cell footprints
→ earthquake association
→ candidate-zone table and figures
```

The default is a strict 95th-percentile threshold: finite processed cells with
values greater than the threshold are anomalous. A uniform field therefore
produces no regions. The alternative robust threshold is
`median + robust_z_threshold × MAD / 0.67449`; a zero-MAD field conservatively
produces no anomaly.

Gaussian smoothing is disabled by default. When enabled, the parameter is in
grid cells and finite-value weights are smoothed separately so NaNs remain
masked. Binary opening and closing are also disabled by default. Connectivity,
minimum component size, and every processing parameter are recorded in
`processing_metadata.json`.

Each component reports its raster-cell count, WGS84 cell area, unweighted cell
centroid, bounding box, maximum and mean selected strain, and maximum-strain
percentile. GeoJSON stores the component's exact raster-cell footprints as a
`MultiPolygon`; it does not imply a continuous geological boundary.

## Earthquakes and spatial association

CSV input accepts case-insensitive forms of:

```text
longitude, latitude, magnitude, time, depth
```

`LON`, `LAT`, `MAG`, `DATE` plus `TIME`, `DEPTH`, and `EVENTID` are also
recognized for the bundled ISC-format catalogue. Invalid rows are counted in
the processing metadata rather than silently disappearing.

Alternatively, a USGS query uses the strain-grid bounds, configurable dates and
minimum magnitude. The raw response and exact parameters are cached in
`usgs_query.json`; an identical rerun uses the cache.

An event is inside a candidate region when it falls in one of its raster cells.
Buffer and nearest-region distances use WGS84 geodesic calculations to the
nearest anomalous cell centre; inside events receive zero distance. This avoids
converting longitude/latitude degrees directly to kilometres, but the
cell-centre representation is still resolution-dependent.

No opaque risk score is calculated. `anomaly_rank` is simply descending maximum
strain, while earthquake counts, magnitudes, distance, and density remain
separate descriptive columns.

## Reproduce

Install the experimental dependencies:

```bash
python -m pip install -e ".[investigation]"
```

Run the deterministic two-anomaly demonstration (it is not observational data):

```bash
python examples/create_synthetic_investigation.py
strain-rate investigate \
  outputs/synthetic-input/strain-rate.nc \
  outputs/synthetic-investigation \
  --earthquakes outputs/synthetic-input/earthquakes.csv \
  --sensitivity-percentiles 90 95 97.5 99
```

Use a local catalogue:

```bash
strain-rate investigate outputs/grid-03/strain-rate.nc outputs/investigation \
  --variable tensor_magnitude \
  --method percentile \
  --percentile 95 \
  --minimum-cells 3 \
  --buffer-km 50 \
  --earthquakes earthquakes.csv \
  --sensitivity-percentiles 90 95 97.5 99
```

Or make and cache a USGS query:

```bash
strain-rate investigate outputs/grid-03/strain-rate.nc outputs/investigation \
  --variable tensor_magnitude \
  --percentile 95 \
  --usgs-start 2000-01-01 \
  --usgs-end 2025-01-01 \
  --minimum-magnitude 4.5
```

Optional preprocessing is explicit, for example:

```bash
strain-rate investigate strain-rate.nc outputs/smoothed \
  --gaussian-sigma-cells 1 \
  --opening-iterations 1 \
  --closing-iterations 1
```

## Outputs

| File | Contents |
| --- | --- |
| `candidate_zones.csv` | ranked strain and earthquake-association statistics |
| `detected_regions.geojson` | geographically referenced raster-cell footprints |
| `investigation_map.png` | strain field, region outlines and earthquake overlay |
| `strain_vs_earthquakes.png` | descriptive anomaly-strength/count diagnostic |
| `processing_metadata.json` | input, parameters, units, provenance and warning |
| `sensitivity_summary.csv` | threshold, zone count, area, cell count and centroids |
| `usgs_query.json` | optional exact query and cached raw USGS response |

## Validation and sensitivity

Automated tests cover a uniform field, one known blob, two disconnected blobs,
NaN masking with smoothing, a boundary anomaly, centroid and region statistics,
threshold sensitivity, standard/ISC-style earthquake fields, cached USGS
responses, inside/outside events, geodesic buffers, nearest distance, no-event
regions, candidate ranking, and complete CLI outputs. Tests never call the live
USGS service.

Sensitivity should be interpreted from all requested thresholds, not just the
preferred map. A stable location that contracts as the threshold rises is more
robust to the threshold choice than a region that appears, disappears, or
fragments. This is segmentation stability—not evidence of earthquake hazard.

For the deterministic demonstration above, version 0.2.0 produces:

| Percentile | Candidate regions | Anomalous cells | Total area (km²) |
| ---: | ---: | ---: | ---: |
| 90 | 12 | 958 | 42,151.77 |
| 95 | 2 | 479 | 21,084.17 |
| 97.5 | 2 | 240 | 10,569.61 |
| 99 | 2 | 96 | 4,238.55 |

At 95–99%, both planted centres remain near `(96.0, 20.0)` and `(97.2, 25.0)`
while their footprints contract. At 90%, ten weak background-wave components
also enter the segmentation. This deliberately illustrates why a single
threshold map is insufficient. These are synthetic validation results and must
not be interpreted as a finding about Myanmar or any observed earthquake.

## Scientific limitations

- Results inherit GNSS processing, reference-frame, station-distribution, and
  interpolation uncertainty.
- Finite differences can amplify noise and boundary artifacts.
- Marginal percentile thresholds do not model spatially varying background
  strain or uncertainty.
- Region shape, area, connectivity, centroid, and buffer results depend on grid
  resolution and configured morphology.
- Earthquake catalogue completeness and location/magnitude uncertainty vary in
  space and time.
- Coincidence can reflect shared tectonic structure, sampling, chance, or other
  confounding factors.
- No null model or statistical significance test is included in this MVP.

**Spatial coincidence between high strain rate and earthquakes does not
demonstrate causality and this tool does not provide earthquake forecasts or
operational hazard assessments.**
