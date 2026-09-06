from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import featuregraph as fg
from featuregraph.utils import _capnobase


def test_capnobase_cases_are_validated() -> None:
    assert _capnobase.normalize_capnobase_case(9) == "0009"
    assert _capnobase.normalize_capnobase_case("0370") == "0370"
    with pytest.raises(ValueError, match="Unknown CapnoBase case"):
        _capnobase.normalize_capnobase_case("0001")


def test_capnobase_signal_loader_standardizes_waveforms(
    monkeypatch, tmp_path: Path
) -> None:
    path = tmp_path / "0009_8min_signal.csv"
    path.write_text("co2_y,pleth_y,ecg_y\n1.5,-0.64,-0.31\n")
    monkeypatch.setattr(_capnobase, "download_capnobase_file", lambda *a, **k: path)

    result = fg.datasets.capnobase("0009")

    assert result.columns.tolist() == [
        "case_id",
        "sample_index",
        "time_seconds",
        "capnogram",
        "ppg",
        "ecg",
    ]
    assert result.iloc[0].to_dict() == {
        "case_id": "0009",
        "sample_index": 0,
        "time_seconds": 0.0,
        "capnogram": 1.5,
        "ppg": -0.64,
        "ecg": -0.31,
    }
    assert result.attrs["source_doi"] == _capnobase.CAPNOBASE_DOI


def test_capnobase_label_loader_makes_events_explicit(
    monkeypatch, tmp_path: Path
) -> None:
    path = tmp_path / "0009_8min_labels.csv"
    pd.DataFrame(
        {
            "co2_startexp_x": [" 974 1990"],
            "co2_startinsp_x": [" 659"],
            "pleth_peak_x": [" 59 242"],
            "units_x": ["samples"],
        }
    ).to_csv(path, index=False)
    monkeypatch.setattr(_capnobase, "download_capnobase_file", lambda *a, **k: path)

    result = fg.datasets.capnobase_labels(9)

    assert len(result) == 5
    assert set(result["event_type"]) == {"co2_startexp", "co2_startinsp", "pleth_peak"}
    first = result.iloc[0]
    assert first["source_sample_number"] == 59
    assert first["sample_index"] == 58
    assert first["time_seconds"] == pytest.approx(58 / 300)


def test_download_uses_borealis_file_id_and_checksum(
    monkeypatch, tmp_path: Path
) -> None:
    content = b"co2_y\tpleth_y\tecg_y\n1\t2\t3\n"
    expected_md5 = __import__("hashlib").md5(content, usedforsecurity=False).hexdigest()
    monkeypatch.setattr(_capnobase, "get_capnobase_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(
        _capnobase,
        "_source_file_record",
        lambda *a, **k: {
            "id": 123,
            "filesize": len(content),
            "checksum": {"type": "MD5", "value": expected_md5},
        },
    )

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            return [content]

    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(_capnobase.requests, "get", get)

    path = _capnobase.download_capnobase_file("0009", "signal")

    assert path.read_bytes() == content
    assert calls[0][0].endswith("/api/access/datafile/123")
    assert calls[0][1]["params"] == {"format": "original"}
