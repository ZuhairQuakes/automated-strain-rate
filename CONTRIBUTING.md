# Contributing

Contributions to the scientific methods, validation cases, documentation, and
software are welcome.

## Development workflow

1. Fork the repository and create a focused branch.
2. Create the Conda environment or install `.[app,dev,investigation,notebook]`.
3. Add tests for numerical or behavioural changes.
4. Run `ruff check .`, `pytest`, `python tools/validate_repository.py`, and
   `python -m build`.
5. Update `SCIENTIFIC_METHOD.md` and `CHANGELOG.md` when behaviour changes.
6. Open a pull request using the repository template.

## Scientific contributions

A method change must state the physical and statistical assumptions, tensor
and sign conventions, coordinate system, units, expected validity domain, and
supporting literature. Include an analytical, synthetic, or peer-reviewed
benchmark with tolerances. Parameter sweeps should report all tested settings,
not only the preferred output.

New observational data must document provider, stable identifier or URL,
access date, reference frame, epoch, processing method, uncertainty definition,
station selection, transformations, and reuse licence. Do not assume the MIT
software licence covers third-party data.

## Notebook policy

The original notebook is retained as a historical research artifact. New
capabilities belong in the tested package first; notebooks should call that
API. Strip execution state before committing:

```bash
python tools/strip_notebook_outputs.py nbtk/*.ipynb
```

Do not commit generated NetCDF grids, GMT temporary files, credentials, or
restricted data.

## Releases

Maintainers synchronize the package version, citation file, and changelog,
merge only green changes, then tag `vX.Y.Z`. GitHub Actions builds the wheel
and source distribution and attaches both to the release.
