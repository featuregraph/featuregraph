"""Run the frozen BIDMC multiscale cardiac-phase contract."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import butter, find_peaks, sosfiltfilt

from featuregraph.studies import load_notebook_namespace


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "notebooks" / ".bidmc_notebook_cache"
NOTEBOOK = ROOT / "notebooks" / "generated_study" / "bidmc_generated_study.ipynb"
OUTPUT = ROOT / "artifacts" / "studies" / "bidmc_multiscale_heldout"
FS = 125
DEVELOPMENT = {13, 19, 23, 33}
TOLERANCE = 63

# The generated study notebook's own development-record cells re-run its
# functions against subject 1 for inline inspection; this runner only needs
# the function and constant definitions that precede that record.
DEFINITIONS_STOP_MARKER = "# Subject 1 development record"


def load_study_namespace() -> dict[str, object]:
    """Execute the generated study's definitions, without its development record."""
    return load_notebook_namespace(
        NOTEBOOK,
        stop_marker=DEFINITIONS_STOP_MARKER,
        name="bidmc_multiscale_audit",
    )


def ecg_events(signal: np.ndarray) -> np.ndarray:
    sos = butter(4, [5, 20], btype="bandpass", fs=FS, output="sos")
    magnitude = np.abs(sosfiltfilt(sos, signal.astype(float)))
    peaks, _ = find_peaks(
        magnitude,
        distance=63,
        prominence=0.5 * np.std(magnitude),
    )
    return peaks


def agreement(primary: np.ndarray, secondary: np.ndarray) -> float:
    if not len(primary) or not len(secondary):
        return 0.0
    return float(np.mean([np.min(np.abs(secondary - peak)) <= 10 for peak in primary]))


def phases(peaks: pd.Series, r_peaks: np.ndarray) -> np.ndarray:
    values = []
    for peak in peaks.dropna().astype(int):
        preceding = np.searchsorted(r_peaks, peak) - 1
        if 0 <= preceding < len(r_peaks) - 1:
            start, end = r_peaks[preceding], r_peaks[preceding + 1]
            values.append((peak - start) / (end - start))
    return np.asarray(values, dtype=float)


def resultant(values: np.ndarray) -> float:
    if len(values) < 5:
        return np.nan
    return float(np.abs(np.mean(np.exp(2j * np.pi * values))))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    ns = load_study_namespace()
    rows = []
    for subject in range(1, 54):
        _, objects_79, _, _ = ns["construct"](subject, 79)
        _, objects_100, _, _ = ns["construct"](subject, 100)
        left = objects_79.loc[objects_79["is_complete"]].sort_values("peak_index").reset_index(drop=True)
        right = objects_100.loc[objects_100["is_complete"]].sort_values("peak_index").reset_index(drop=True)
        pairs = ns["optimal_pairs"](
            left["peak_index"].tolist(), right["peak_index"].tolist(), TOLERANCE
        )
        shared_indices = {index for index, _ in pairs}
        shared = left.loc[left.index.isin(shared_indices)]
        extra = left.loc[~left.index.isin(shared_indices)]

        signals = ns["load"](subject)
        r_by_lead = {
            lead: ecg_events(signals[lead].astype(float).to_numpy())
            for lead in ("II", "V", "AVR")
            if lead in signals.columns
        }
        numerics = pd.read_csv(CACHE / f"bidmc_{subject:02d}_Numerics.csv")
        numerics.columns = numerics.columns.str.strip()
        monitor_hr = numerics["HR"].dropna().astype(float)
        primary = r_by_lead["II"]
        duration_minutes = len(signals) / FS / 60
        derived_hr = len(primary) / duration_minutes
        secondary_agreements = [
            agreement(primary, r_by_lead[lead])
            for lead in ("V", "AVR")
            if lead in r_by_lead
        ]
        secondary_agreement = max(secondary_agreements, default=0.0)
        reasons = []
        if monitor_hr.empty:
            reasons.append("monitor_hr_missing")
        elif monitor_hr.max() >= 119:
            reasons.append("monitor_hr_outside_refractory_contract")
        monitor_median = float(monitor_hr.median()) if not monitor_hr.empty else np.nan
        if not monitor_hr.empty and abs(derived_hr - monitor_median) > 5:
            reasons.append("derived_monitor_hr_difference_gt_5")
        if secondary_agreement < 0.90:
            reasons.append("cross_lead_agreement_lt_0.90")
        valid = not reasons

        annotations = ns["load"](subject, "Breaths")
        annotation_values = [
            annotations[column].dropna().astype(int).to_numpy()
            for column in (
                "breaths ann1 [signal sample no]",
                "breaths ann2 [signal sample no]",
            )
        ]
        supported = [
            any(np.min(np.abs(values - int(peak))) <= TOLERANCE for values in annotation_values if len(values))
            for peak in extra["peak_index"]
        ]
        shared_phase = phases(shared["peak_index"], primary) if valid else np.array([])
        extra_phase = phases(extra["peak_index"], primary) if valid else np.array([])
        shared_r = resultant(shared_phase) if valid else np.nan
        extra_r = resultant(extra_phase) if valid else np.nan
        extra_rates = 60 / extra["period_seconds"].replace([np.inf, -np.inf], np.nan).dropna()
        rows.append(
            {
                "subject": subject,
                "cohort": "development" if subject in DEVELOPMENT else "held_out",
                "ecg_valid": valid,
                "exclusion_reason": ";".join(reasons),
                "monitor_hr_median": monitor_median,
                "monitor_hr_max": float(monitor_hr.max()) if not monitor_hr.empty else np.nan,
                "ecg_derived_hr": derived_hr,
                "cross_lead_agreement": secondary_agreement,
                "objects_79": len(left),
                "objects_100": len(right),
                "shared_objects": len(shared),
                "objects_79_only": len(extra),
                "shared_phase_n": len(shared_phase),
                "objects_79_only_phase_n": len(extra_phase),
                "shared_phase_resultant": shared_r,
                "objects_79_only_phase_resultant": extra_r,
                "phase_resultant_difference": extra_r - shared_r,
                "objects_79_only_annotation_supported": int(sum(supported)),
                "objects_79_only_annotation_supported_fraction": float(np.mean(supported)) if supported else np.nan,
                "objects_79_only_rate_median": float(extra_rates.median()) if len(extra_rates) else np.nan,
            }
        )

    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT / "subject_summary.csv", index=False)
    held = summary[(summary["cohort"] == "held_out") & summary["ecg_valid"]]
    eligible = held["phase_resultant_difference"].dropna()
    report = f"""# Held-out BIDMC multiscale cardiac-phase result

- Held-out subjects: {int((summary['cohort'] == 'held_out').sum())}
- ECG-valid held-out subjects: {len(held)}
- Subjects eligible for both concentration estimates: {len(eligible)}
- Positive phase-concentration differences: {int((eligible > 0).sum())} of {len(eligible)}
- Median subject-level difference: {eligible.median():.3f}
- Held-out W=79-only objects: {int(held['objects_79_only'].sum())}
- Annotation-supported W=79-only objects: {int(held['objects_79_only_annotation_supported'].sum())}
- Annotation-supported fraction: {held['objects_79_only_annotation_supported'].sum() / held['objects_79_only'].sum():.3f}

The primary outcome is descriptive under the frozen contract. No ECG,
cross-window, phase, or annotation parameter was changed after held-out execution.
"""
    (OUTPUT / "report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
