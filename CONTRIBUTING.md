# Contributing

Thank you for helping improve this research repository.

## Workflow

1. Create the Conda environment from [`environment.yml`](environment.yml).
2. Install GMT separately and confirm that `gmt --version` works.
3. Keep the tracked source velocity field immutable; add a new, documented file for a different dataset.
4. Do not commit NetCDF grids or temporary `gpsgridder` files. These are reproducible outputs and are ignored by Git.

Run the structural checks before opening a pull request:

```bash
python tools/validate_repository.py
```

Clear notebook execution state before committing with `python tools/strip_notebook_outputs.py nbtk/*.ipynb`.

Pull requests that change interpolation settings should report the GMT version, grid interval, Poisson ratio, eigenvalue cutoff, and the resulting figure or summary statistic.
