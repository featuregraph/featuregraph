"""The region inspector draws from cached files and reports the occurrences."""

from pathlib import Path

import numpy as np
import pandas as pd

from scripts import inspect_bidmc_region as inspect


def _synthetic_cache(directory: Path, subject: int = 7) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    n = 6001
    t = np.arange(n) / inspect.FS
    rng = np.random.default_rng(1)
    resp = np.sin(2 * np.pi * 0.25 * t) + 0.1 * np.sin(2 * np.pi * 1.4 * t)
    resp += 0.03 * rng.standard_normal(n)
    ecg = 0.02 * rng.standard_normal(n)
    ecg[::90] += 1.0
    pd.DataFrame({"Time [s]": t, "RESP": resp, "II": ecg}).to_csv(
        directory / f"bidmc_{subject:02d}_Signals.csv", index=False
    )
    pd.DataFrame(
        {
            "breaths ann1 [signal sample no]": [400, 900, 1400],
            "breaths ann2 [signal sample no]": [410, 905, np.nan],
        }
    ).to_csv(directory / f"bidmc_{subject:02d}_Breaths.csv", index=False)
    return directory


def test_draw_writes_one_image_and_one_table_per_window(tmp_path: Path):
    cache = _synthetic_cache(tmp_path / "cache")

    path, tables = inspect.draw(
        7, 300, 1500, [79, 100], cache=cache, output=tmp_path / "out"
    )

    assert path.exists() and path.stat().st_size > 0
    assert set(tables) == {79, 100}
    for table in tables.values():
        assert {"state", "start_position", "end_position", "asymmetry"} <= set(
            table.columns
        )
        assert (table["end_position"] >= 300).all()
        assert (table["start_position"] <= 1500).all()
        assert table.loc[table["state"] != "rising", "asymmetry"].isna().all()


def test_region_occurrences_keep_only_what_touches_the_region(tmp_path: Path):
    cache = _synthetic_cache(tmp_path / "cache")
    raw = inspect.fetch(7, "Signals", cache)["RESP"].astype(float)
    compiled = inspect.compile_window(raw, 7, 79)

    everything = inspect.region_occurrences(compiled, 0, len(raw))
    window = inspect.region_occurrences(compiled, 1000, 1100)

    assert len(window) < len(everything)
    assert (window["end_position"] >= 1000).all()
    assert (window["start_position"] <= 1100).all()


def test_main_prints_the_tables_and_the_path(tmp_path: Path, capsys):
    cache = _synthetic_cache(tmp_path / "cache")

    code = inspect.main(
        [
            "--subject",
            "7",
            "--start",
            "300",
            "--end",
            "1500",
            "--window",
            "79",
            "100",
            "--cache",
            str(cache),
            "--output",
            str(tmp_path / "out"),
        ]
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "W = 79:" in out and "W = 100:" in out
    assert "bidmc_07_300_1500_W79_100.png" in out
