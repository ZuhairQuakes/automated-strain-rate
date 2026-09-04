from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from automated_strain_rate.earthquakes import (
    catalog_from_usgs_geojson,
    normalize_earthquake_catalog,
    query_usgs_catalog,
    read_earthquake_catalog,
)


def _usgs_payload() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "test-event",
                "properties": {"mag": 5.2, "time": 1_735_689_600_000},
                "geometry": {"type": "Point", "coordinates": [101.2, 1.5, 12.0]},
            }
        ],
    }


def test_normalizes_required_columns_and_discards_invalid_rows() -> None:
    frame = pd.DataFrame(
        {
            "LON": [101.0, "bad"],
            "LAT": [1.0, 2.0],
            "MAG": [5.0, 4.0],
            "DEPTH": [10.0, 20.0],
            "DATE": ["01-01-2025", "02-01-2025"],
            "TIME": ["12:30:00", "13:30:00"],
        }
    )

    result = normalize_earthquake_catalog(frame)

    assert len(result) == 1
    assert result.attrs["discarded_rows"] == 1
    assert str(result.loc[0, "time"].tz) == "UTC"


def test_reads_standard_csv_catalogue(tmp_path: Path) -> None:
    source = tmp_path / "earthquakes.csv"
    source.write_text(
        "longitude,latitude,magnitude,time,depth\n101,1,5.5,2025-01-01T00:00:00Z,15\n",
        encoding="utf-8",
    )

    result = read_earthquake_catalog(source)

    assert result.loc[0, "magnitude"] == 5.5


def test_validates_usgs_geojson() -> None:
    result = catalog_from_usgs_geojson(_usgs_payload())

    assert result.loc[0, "event_id"] == "test-event"
    assert result.loc[0, "depth"] == 12.0


def test_usgs_query_cache_avoids_second_download(tmp_path: Path) -> None:
    calls: list[str] = []

    def downloader(url: str, timeout: float) -> dict:
        calls.append(f"{url}:{timeout}")
        return _usgs_payload()

    arguments = {
        "bounds": (100.0, 102.0, 0.0, 3.0),
        "start_time": "2025-01-01",
        "end_time": "2025-02-01",
        "minimum_magnitude": 4.5,
        "cache_path": tmp_path / "query.json",
        "downloader": downloader,
    }
    first, first_metadata = query_usgs_catalog(**arguments)
    second, second_metadata = query_usgs_catalog(**arguments)

    assert len(calls) == 1
    assert len(first) == len(second) == 1
    assert not first_metadata["cache_used"]
    assert second_metadata["cache_used"]
    saved = json.loads((tmp_path / "query.json").read_text(encoding="utf-8"))
    assert saved["query"]["minmagnitude"] == 4.5
