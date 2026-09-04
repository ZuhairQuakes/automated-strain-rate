# Scientific method and conventions

Automated Strain Rate estimates infinitesimal two-dimensional crustal strain
from an interpolated horizontal GNSS velocity field. It does not establish a
tectonic mechanism or quantify earthquake probability.

The optional anomaly and earthquake-association experiment is isolated from
this numerical core and documented in
[`EXPERIMENTAL_ANOMALY_EXPLORER.md`](EXPERIMENTAL_ANOMALY_EXPLORER.md).

## Coordinate approximation

Longitude and latitude are mapped to a local equirectangular frame at the mean
grid latitude:

```text
x = longitude × 111.195 km × cos(mean latitude)
y = latitude  × 111.195 km
```

This approximation is transparent and deterministic but increasingly
inaccurate for large regions, high latitudes, or grids crossing the antimeridian.
Use an appropriate projected coordinate reference system for those cases.

## Tensor calculation

For east velocity `u` and north velocity `v`, finite differences produce:

```text
exx = du/dx
eyy = dv/dy
exy = 0.5 × (du/dy + dv/dx)
rotation = 0.5 × (dv/dx - du/dy)
dilatation = exx + eyy
maximum_shear = sqrt(((exx - eyy) / 2)^2 + exy^2)
principal_maximum/minimum = dilatation / 2 ± maximum_shear
tensor_magnitude = sqrt(exx^2 + eyy^2 + 2 exy^2)
```

`maximum_shear` is half the principal-strain difference, not engineering shear.
`tensor_magnitude` preserves the historical notebook's quantity, previously
labelled “second invariant”; the explicit name avoids implying a different
invariant convention.

Velocities in millimetres/year divided by distance in kilometres are reported
as microstrain/year. Rotation has the corresponding microradian/year scale.
Positive `exx` and `eyy` denote extension; positive rotation is counter-clockwise
under the east/north axis convention.

## Interpolation

The optional pipeline uses GMT `gpsgridder`. Record GMT version, region, grid
registration, spacing, Poisson ratio, fudge factor, eigenvalue cutoff, input
stations, and software commit. The current adapter interpolates east and north
velocities and does not weight observations by their stated uncertainties.

Spatial differentiation amplifies interpolation artifacts and measurement
noise. Grid-spacing sensitivity is necessary but does not replace uncertainty
propagation, cross-validation, or comparison with an independent method.

## Validation and uncertainty

The automated test suite checks an affine velocity field whose derivatives are
known analytically. A real study should additionally evaluate station holdouts,
boundary effects, correlated errors, reference-frame uncertainty, interpolation
hyperparameters, and alternative projections. Output precision is not evidence
of physical accuracy.

## Responsible interpretation

- Results near grid boundaries are especially sensitive to finite differences.
- Sparse or uneven station geometry can create unsupported spatial structure.
- Vertical deformation is not included in the two-dimensional tensor.
- The workflow does not model coseismic offsets, transient motion, or temporal
  correlation unless those effects were removed upstream.
- Outputs are research estimates, not official warnings or hazard products.
