"""Summarise the per-subject peak tables the region inspector writes.

``scripts/inspect_bidmc_region.py --peaks`` writes one table per subject with a
row for every object peak at W=79: whether a W=100 peak lies within 63
samples, the lag from the preceding R-peak, the cardiac phase, and the breath
phase between W=100 peaks. This script reduces those 53 tables to one row per
subject and places each row beside the frozen held-out study's row for the
same subject, so the two constructions can be compared without either being
recomputed.

The inspector and the frozen study are not the same construction. The study
builds trough-to-trough objects, keeps only complete ones, places each peak
at the midpoint of the envelope's flat run, and pairs the two windows
one-to-one by an optimal assignment. The inspector counts every exit-rising
event, places the peak on the exit sample, and calls a peak matched when any
W=100 peak lies within the tolerance. The frozen study's numbers are the
published ones; the inspector's are a check on them.

Usage::

    python -m scripts.summarize_bidmc_peak_measures
    python -m scripts.summarize_bidmc_peak_measures --peaks-dir DIR \\
        --heldout-summary CSV --output CSV
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "artifacts" / "studies" / "bidmc_peak_measures"
HELDOUT_SUMMARY = (
    ROOT / "artifacts" / "studies" / "bidmc_multiscale_heldout" / "subject_summary.csv"
)
OUTPUT = STUDY / "subject_summary.csv"
DEVELOPMENT_SUBJECTS = (3, 13, 19, 23, 33)
MIN_PHASES = 5
# One RR interval at the cohort's heart rates, in samples at 125 Hz, taken
# generously: a W=79-only peak this far from the nearest W=100 peak sits one
# heartbeat away from it.
ONE_RR = (64, 130)

HELDOUT_COLUMNS = [
    "cohort",
    "ecg_valid",
    "exclusion_reason",
    "monitor_hr_median",
    "objects_79",
    "objects_100",
    "objects_79_only",
    "shared_phase_resultant",
    "objects_79_only_phase_resultant",
]


def resultant(phase: pd.Series | np.ndarray) -> float:
    """Length of the mean phase vector, NaN below the study's minimum count."""
    values = np.asarray(phase, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < MIN_PHASES:
        return float("nan")
    return float(np.abs(np.mean(np.exp(2j * np.pi * values))))


def summarise_subject(table: pd.DataFrame) -> dict[str, float]:
    matched = table[table["matched"]]
    unmatched = table[~table["matched"]]
    nearest = unmatched["nearest_coarse_peak"]
    lag = table["r_lag"]
    return {
        "peaks_79": len(table),
        "matched": len(matched),
        "unmatched": len(unmatched),
        "unmatched_one_rr_from_w100": int(
            ((nearest >= ONE_RR[0]) & (nearest <= ONE_RR[1])).sum()
        ),
        "resultant_matched": resultant(matched["cardiac_phase"]),
        "resultant_unmatched": resultant(unmatched["cardiac_phase"]),
        "resultant_all": resultant(table["cardiac_phase"]),
        "r_lag_median": float(lag.median()),
        "r_lag_iqr": float(lag.quantile(0.75) - lag.quantile(0.25)),
        "breath_phase_unmatched_min": float(unmatched["breath_phase"].min()),
        "breath_phase_unmatched_max": float(unmatched["breath_phase"].max()),
    }


def summarise(peaks_dir: Path, heldout_summary: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(peaks_dir.glob("bidmc_*_peaks_W79_100.csv")):
        subject = int(path.name.split("_")[1])
        table = pd.read_csv(path)
        rows.append({"subject": subject, **summarise_subject(table)})
    if not rows:
        raise FileNotFoundError(f"no peak tables under {peaks_dir}")
    summary = pd.DataFrame(rows)
    heldout = pd.read_csv(heldout_summary)
    summary = summary.merge(
        heldout[["subject", *HELDOUT_COLUMNS]], on="subject", how="left"
    )
    summary["development"] = summary["subject"].isin(DEVELOPMENT_SUBJECTS)
    return summary


def describe(summary: pd.DataFrame) -> str:
    valid = summary[summary["ecg_valid"].fillna(False).astype(bool)]
    eligible = valid[valid["resultant_unmatched"].notna()]
    locked = eligible[eligible["resultant_unmatched"] >= 0.9]
    shared_locked = valid[valid["resultant_matched"] >= 0.8]
    study_locked = valid[valid["objects_79_only_phase_resultant"] >= 0.9]
    lines = [
        f"subjects: {len(summary)}",
        f"ECG-valid: {len(valid)}",
        f"ECG-valid with at least {MIN_PHASES} unmatched phases: {len(eligible)}",
        "unmatched resultant >= 0.9: "
        f"{len(locked)} ({', '.join(map(str, locked['subject']))})",
        "frozen study W=79-only resultant >= 0.9: "
        f"{len(study_locked)} ({', '.join(map(str, study_locked['subject']))})",
        "matched resultant >= 0.8: "
        f"{len(shared_locked)} ({', '.join(map(str, shared_locked['subject']))})",
        f"median r_lag IQR, ECG-valid: {valid['r_lag_iqr'].median():.1f} samples",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--peaks-dir", type=Path, default=STUDY)
    parser.add_argument("--heldout-summary", type=Path, default=HELDOUT_SUMMARY)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    summary = summarise(args.peaks_dir, args.heldout_summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output, index=False, float_format="%.6g")
    print(describe(summary))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
