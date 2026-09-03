"""Run the frozen BIDMC multiscale cardiac-phase contract.

Writes ``subject_summary.csv`` and ``report.md`` under the study directory,
plus ``provenance.json``: the commit the run was made from, whether the tree
was clean, the software versions, and the SHA-256 of each output.

``--check`` runs the construction into a temporary directory and compares
every output byte for byte against the committed files, so a reader can
confirm that the frozen artifacts are what this code produces at a known
commit. It leaves the committed CSV and report untouched, records the
outcome in ``provenance.json``, and exits non-zero on any difference.

Needs the BIDMC source files, downloaded from PhysioNet into
``notebooks/.bidmc_notebook_cache`` on first use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
import scipy
from scipy.signal import butter, find_peaks, sosfiltfilt

import featuregraph
from featuregraph.studies import load_notebook_namespace
from featuregraph.studies.provenance import git_commit_or_none, git_status_clean

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


DOWNLOAD_ATTEMPTS = 4


def load_numerics(ns: dict[str, object], subject: int) -> pd.DataFrame:
    """Fetch the monitor numerics the notebook's loader does not cover.

    PhysioNet answers with a gateway error now and then. A failed attempt
    leaves nothing behind and is retried with backoff; a file that arrives
    without the monitor heart-rate column is discarded and fetched again.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"bidmc_{subject:02d}_Numerics.csv"
    url = f"{ns['BASE']}/{path.name}"
    last_error: Exception | None = None
    for attempt in range(DOWNLOAD_ATTEMPTS):
        try:
            if not path.exists():
                urlretrieve(url, path)
            numerics = pd.read_csv(path)
            numerics.columns = numerics.columns.str.strip()
            if "HR" not in numerics.columns:
                raise ValueError(f"{path.name} has no HR column")
            return numerics
        except (OSError, ValueError, pd.errors.ParserError) as error:
            last_error = error
            path.unlink(missing_ok=True)
            if attempt < DOWNLOAD_ATTEMPTS - 1:
                time.sleep(2**attempt)
    raise RuntimeError(
        f"Could not fetch a valid BIDMC numerics file after {DOWNLOAD_ATTEMPTS} "
        f"attempts: {url}"
    ) from last_error


def run(output: Path) -> None:
    """Execute the frozen contract for every subject and write the outputs."""
    output.mkdir(parents=True, exist_ok=True)
    ns = load_study_namespace()
    rows = []
    for subject in range(1, 54):
        _, objects_79, _, _ = ns["construct"](subject, 79)
        _, objects_100, _, _ = ns["construct"](subject, 100)
        left = (
            objects_79.loc[objects_79["is_complete"]]
            .sort_values("peak_index")
            .reset_index(drop=True)
        )
        right = (
            objects_100.loc[objects_100["is_complete"]]
            .sort_values("peak_index")
            .reset_index(drop=True)
        )
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
        numerics = load_numerics(ns, subject)
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
            any(
                np.min(np.abs(values - int(peak))) <= TOLERANCE
                for values in annotation_values
                if len(values)
            )
            for peak in extra["peak_index"]
        ]
        shared_phase = phases(shared["peak_index"], primary) if valid else np.array([])
        extra_phase = phases(extra["peak_index"], primary) if valid else np.array([])
        shared_r = resultant(shared_phase) if valid else np.nan
        extra_r = resultant(extra_phase) if valid else np.nan
        extra_rates = (
            60 / extra["period_seconds"].replace([np.inf, -np.inf], np.nan).dropna()
        )
        rows.append(
            {
                "subject": subject,
                "cohort": "development" if subject in DEVELOPMENT else "held_out",
                "ecg_valid": valid,
                "exclusion_reason": ";".join(reasons),
                "monitor_hr_median": monitor_median,
                "monitor_hr_max": float(monitor_hr.max())
                if not monitor_hr.empty
                else np.nan,
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
                "objects_79_only_annotation_supported_fraction": float(
                    np.mean(supported)
                )
                if supported
                else np.nan,
                "objects_79_only_rate_median": float(extra_rates.median())
                if len(extra_rates)
                else np.nan,
            }
        )

    summary = pd.DataFrame(rows)
    summary.to_csv(output / "subject_summary.csv", index=False)
    held = summary[(summary["cohort"] == "held_out") & summary["ecg_valid"]]
    eligible = held["phase_resultant_difference"].dropna()
    held_out_total = int((summary["cohort"] == "held_out").sum())
    positive = int((eligible > 0).sum())
    extra_total = int(held["objects_79_only"].sum())
    supported_total = int(held["objects_79_only_annotation_supported"].sum())
    supported_fraction = supported_total / extra_total
    report = f"""# Held-out BIDMC multiscale cardiac-phase result

- Held-out subjects: {held_out_total}
- ECG-valid held-out subjects: {len(held)}
- Subjects eligible for both concentration estimates: {len(eligible)}
- Positive phase-concentration differences: {positive} of {len(eligible)}
- Median subject-level difference: {eligible.median():.3f}
- Held-out W=79-only objects: {extra_total}
- Annotation-supported W=79-only objects: {supported_total}
- Annotation-supported fraction: {supported_fraction:.3f}

The primary outcome is descriptive under the frozen contract. No ECG,
cross-window, phase, or annotation parameter was changed after held-out execution.
"""
    (output / "report.md").write_text(report)
    print(report)


OUTPUT_FILES = ("subject_summary.csv", "report.md")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def provenance(produced: Path, check: dict[str, object] | None = None) -> dict:
    """What produced the outputs, and whether it reproduced the committed ones."""
    record: dict[str, object] = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_or_none(ROOT),
        "git_tree_clean": git_status_clean(ROOT),
        "featuregraph_version": featuregraph.__version__,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "scipy_version": scipy.__version__,
        "platform": platform.platform(),
        "outputs": {name: sha256(produced / name) for name in OUTPUT_FILES},
    }
    if check is not None:
        record["check"] = check
    return record


def compare(produced: Path, committed: Path) -> dict[str, object]:
    """Byte-for-byte comparison of every output against the committed file."""
    files = {}
    for name in OUTPUT_FILES:
        fresh = sha256(produced / name)
        frozen = sha256(committed / name) if (committed / name).exists() else None
        files[name] = {
            "produced": fresh,
            "committed": frozen,
            "identical": fresh == frozen,
        }
    try:
        compared_against = str(committed.relative_to(ROOT))
    except ValueError:
        compared_against = str(committed)
    return {
        "compared_against": compared_against,
        "files": files,
        "identical": all(entry["identical"] for entry in files.values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="run into a temporary directory and compare with the committed outputs",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT,
        help="where to write outputs (default: the study directory)",
    )
    args = parser.parse_args(argv)

    if not args.check:
        run(args.output_dir)
        record = provenance(args.output_dir)
        (args.output_dir / "provenance.json").write_text(
            json.dumps(record, indent=2) + "\n"
        )
        return 0

    with tempfile.TemporaryDirectory(prefix="bidmc_heldout_check_") as tmp:
        produced = Path(tmp)
        run(produced)
        check = compare(produced, args.output_dir)
        record = provenance(produced, check)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "provenance.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    for name, entry in check["files"].items():
        print(f"{name}: {'identical' if entry['identical'] else 'DIFFERENT'}")
    print(f"commit {record['git_commit']} clean={record['git_tree_clean']}")
    return 0 if check["identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
