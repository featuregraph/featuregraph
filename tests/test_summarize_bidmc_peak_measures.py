"""The peak-measure summary reduces inspector tables and joins the frozen study."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import summarize_bidmc_peak_measures as summarize


def _peaks(directory: Path, subject: int, phases: np.ndarray, matched: np.ndarray):
    n = len(phases)
    pd.DataFrame(
        {
            "position": np.arange(n) * 120 + 200,
            "nearest_coarse_peak": np.where(matched, 0, 110),
            "matched": matched,
            "r_lag": np.round(phases * 112),
            "cardiac_phase": phases,
            "breath_phase": np.where(matched, 0.0, 0.33),
        }
    ).to_csv(directory / f"bidmc_{subject:02d}_peaks_W79_100.csv", index=False)


@pytest.fixture
def study(tmp_path: Path) -> tuple[Path, Path]:
    peaks = tmp_path / "peaks"
    peaks.mkdir()
    rng = np.random.default_rng(3)
    # Subject 13-like: everything locked; subject 1-like: nothing unmatched.
    _peaks(peaks, 13, np.full(40, 0.34), np.arange(40) % 2 == 0)
    _peaks(peaks, 1, rng.uniform(size=40), np.ones(40, dtype=bool))
    heldout = tmp_path / "heldout.csv"
    pd.DataFrame(
        {
            "subject": [1, 13],
            "cohort": ["held_out", "development"],
            "ecg_valid": [True, True],
            "exclusion_reason": [np.nan, np.nan],
            "monitor_hr_median": [91.0, 67.0],
            "objects_79": [40, 40],
            "objects_100": [40, 20],
            "objects_79_only": [0, 20],
            "shared_phase_resultant": [0.3, 0.95],
            "objects_79_only_phase_resultant": [np.nan, 0.99],
        }
    ).to_csv(heldout, index=False)
    return peaks, heldout


def test_summary_has_one_row_per_subject_with_study_columns(study):
    peaks, heldout = study

    summary = summarize.summarise(peaks, heldout).set_index("subject")

    assert list(summary.index) == [1, 13]
    row = summary.loc[13]
    assert row["peaks_79"] == 40 and row["matched"] == 20 and row["unmatched"] == 20
    assert row["unmatched_one_rr_from_w100"] == 20
    assert row["resultant_unmatched"] == pytest.approx(1.0)
    assert row["resultant_matched"] == pytest.approx(1.0)
    assert row["monitor_hr_median"] == 67.0 and row["development"]
    assert np.isnan(summary.loc[1, "resultant_unmatched"])
    assert summary.loc[1, "resultant_all"] < 0.5
    assert not summary.loc[1, "development"]


def test_resultant_needs_five_phases():
    assert np.isnan(summarize.resultant(np.array([0.2] * 4)))
    assert summarize.resultant(np.array([0.2] * 5)) == pytest.approx(1.0)


def test_main_writes_the_csv_and_describes_the_cohort(study, tmp_path: Path, capsys):
    peaks, heldout = study
    output = tmp_path / "out" / "subject_summary.csv"

    code = summarize.main(
        [
            "--peaks-dir",
            str(peaks),
            "--heldout-summary",
            str(heldout),
            "--output",
            str(output),
        ]
    )

    out = capsys.readouterr().out
    assert code == 0
    assert output.exists()
    assert "unmatched resultant >= 0.9: 1 (13)" in out
    assert "matched resultant >= 0.8: 1 (13)" in out


def test_missing_tables_is_an_error(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        summarize.summarise(tmp_path, tmp_path / "none.csv")
