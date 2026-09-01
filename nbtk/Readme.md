# Historical notebook

`strain_rates_compute.ipynb` is the exploratory workflow that motivated the
tested package. It mixes interpolation, file management, tensor calculation,
and plotting in one document and is retained for provenance.

For new analyses, use the `automated_strain_rate` API or `strain-rate` CLI.
Those interfaces avoid shell pipelines, record units and parameters in NetCDF
metadata, and are covered by analytical tests.
