"""Figure 1 draws from cached signals and is skipped cleanly without them."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import analyze_bidmc_subject13_multiscale as audit
from scripts import plot_bidmc_paper_figures as figures


def _synthetic_cache(directory: Path) -> Path:
    """Sixty thousand samples of a breathing-like trace and a spiky ECG."""
    directory.mkdir(parents=True, exist_ok=True)
    n = 60001
    t = np.arange(n) / audit.FS
    rng = np.random.default_rng(0)
    resp = np.sin(2 * np.pi * 0.25 * t) + 0.05 * rng.standard_normal(n)
    ecg = 0.02 * rng.standard_normal(n)
    ecg[::100] += 1.0  # an R-peak every 0.8 seconds
    pd.DataFrame({"Time [s]": t, "RESP": resp, "II": ecg}).to_csv(
        directory / "bidmc_13_Signals.csv", index=False
    )
    pd.DataFrame(
        {
            "breaths ann1 [signal sample no]": [700, 1100],
            "breaths ann2 [signal sample no]": [720, np.nan],
        }
    ).to_csv(directory / "bidmc_13_Breaths.csv", index=False)
    return directory


def test_region_construction_returns_the_stated_objects(tmp_path: Path):
    cache = _synthetic_cache(tmp_path)

    c = audit.region_construction(cache)

    assert c["peaks_79"].tolist() == [731, 848, 951, 1069]
    assert c["peaks_100"].tolist() == [848]
    assert (c["preceding_r"] <= c["peaks_79"]).all()
    assert c["annotation_1"].tolist() == [700, 1100]
    assert c["annotation_2"].tolist() == [720]


def test_figure_1_is_drawn_from_the_cache(tmp_path: Path, monkeypatch):
    cache = _synthetic_cache(tmp_path / "cache")
    out = tmp_path / "figures"
    monkeypatch.setattr(figures, "FIGURES", out)
    figures.style()

    drawn = figures.figure_construction(cache)

    assert drawn is True
    for suffix in ("png", "svg", "pdf"):
        assert (out / f"fig1_subject13_construction.{suffix}").stat().st_size > 0


def test_figure_1_is_skipped_without_the_cache(tmp_path: Path, monkeypatch, capsys):
    out = tmp_path / "figures"
    monkeypatch.setattr(figures, "FIGURES", out)

    drawn = figures.figure_construction(tmp_path / "empty")

    assert drawn is False
    assert "skipping fig1" in capsys.readouterr().out
    assert not out.exists()


def test_regenerated_figure_files_are_byte_identical(tmp_path: Path, monkeypatch):
    """No timestamp in any output, so a re-run leaves a clean tree."""
    import hashlib
    import time

    cache = _synthetic_cache(tmp_path / "cache")
    out = tmp_path / "figures"
    monkeypatch.setattr(figures, "FIGURES", out)
    figures.style()

    def digests() -> dict[str, str]:
        return {
            suffix: hashlib.sha256(
                (out / f"fig1_subject13_construction.{suffix}").read_bytes()
            ).hexdigest()
            for suffix in ("png", "svg", "pdf")
        }

    figures.figure_construction(cache)
    first = digests()
    time.sleep(1.1)  # a creation date would differ at second resolution
    figures.figure_construction(cache)

    assert digests() == first


def _synthetic_peaks(directory: Path, subject: int = 13) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(5)
    n = 60
    lag = np.round(39 + rng.normal(0, 1.5, n))
    lag[:3] = [95, 26, 88]  # a few breaths whose exit fell between bumps
    pd.DataFrame(
        {
            "position": np.arange(n) * 140 + 200,
            "nearest_coarse_peak": np.where(np.arange(n) % 2 == 0, 0, 112),
            "matched": np.arange(n) % 2 == 0,
            "r_lag": lag,
            "cardiac_phase": lag / 112,
            "breath_phase": np.where(np.arange(n) % 2 == 0, 0.0, 0.33),
        }
    ).to_csv(directory / f"bidmc_{subject:02d}_peaks_W79_100.csv", index=False)
    return directory


def test_figure_5_is_drawn_from_the_peak_table(tmp_path: Path, monkeypatch):
    out = tmp_path / "figures"
    monkeypatch.setattr(figures, "FIGURES", out)
    monkeypatch.setattr(figures, "PEAK_MEASURES", _synthetic_peaks(tmp_path / "peaks"))
    figures.style()

    figures.figure_lag_histogram()

    for suffix in ("png", "svg", "pdf"):
        assert (out / f"fig5_subject13_lag_histogram.{suffix}").stat().st_size > 0


def test_figure_5_reads_the_committed_subject_13_table(tmp_path: Path, monkeypatch):
    """The committed table is the paper's source; the figure must draw from it."""
    if not (figures.PEAK_MEASURES / "bidmc_13_peaks_W79_100.csv").exists():
        pytest.skip("peak tables not present")
    out = tmp_path / "figures"
    monkeypatch.setattr(figures, "FIGURES", out)
    figures.style()

    figures.figure_lag_histogram()

    assert (out / "fig5_subject13_lag_histogram.pdf").stat().st_size > 0
