# Data

`mymr_vel_space_ITRF2014.txt` is an example GNSS velocity field for Myanmar in
the whitespace-delimited schema:

```text
Lon Lat Ve Vn Vu Se Sn Su Name
```

The filename identifies ITRF2014, but the repository history does not provide
a complete upstream citation, processing description, epoch, or explicit data
licence. Treat this file as a legacy reproducibility fixture until those details
are confirmed. Do not assume the repository's MIT software licence grants reuse
rights over the observations.

For any contributed dataset, document:

- provider, authors, DOI or stable URL, and access date;
- reference frame, epoch, velocity and uncertainty units;
- processing solution and transformations;
- station selection, exclusions, and duplicate handling;
- geographic and temporal coverage; and
- licence or permission for redistribution.

Generated NetCDF interpolation and strain grids belong in an ignored output
directory and should be regenerated from documented inputs and parameters.
