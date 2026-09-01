"""Execute a versioned BIDMC rolling-envelope parameter study.

The object construction, state contract, completeness rules, comparator, and
matching tolerance are loaded from the frozen generated BIDMC study. Only the
declared rolling-envelope window changes. The default execution evaluates an
85-sample request and compares it with the registered 79- and 100-sample
variants.
"""

from __future__ import annotations

import argparse
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

from featuregraph.studies import (
    finite_summary,
    markdown_table,
    value_sha256,
    write_csv_shards,
    write_json,
)
from scripts.run_bidmc_multiscale_heldout import load_study_namespace


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "studies" / "bidmc_window_85"
FS = 125
SUBJECTS = tuple(range(1, 54))
REGISTERED_WINDOWS = (79, 100)
PAIR_TOLERANCE = 63


def complete(objects: pd.DataFrame) -> pd.DataFrame:
    return objects.loc[objects["is_complete"]].sort_values("peak_index").reset_index(drop=True)


def compare_windows(ns: dict[str, object], left: pd.DataFrame, right: pd.DataFrame) -> dict[str, int]:
    pairs = ns["optimal_pairs"](
        left["peak_index"].tolist(), right["peak_index"].tolist(), PAIR_TOLERANCE
    )
    return {
        "shared_objects": len(pairs),
        "left_only_objects": len(left) - len(pairs),
        "right_only_objects": len(right) - len(pairs),
    }


def run_subject(ns: dict[str, object], subject: int, requested_window: int) -> dict[str, object]:
    frames: dict[int, pd.DataFrame] = {}
    objects_by_window: dict[int, pd.DataFrame] = {}
    invalidated_by_window: dict[int, pd.DataFrame] = {}
    detected_by_window: dict[int, list[int]] = {}
    for window in sorted(set((*REGISTERED_WINDOWS, requested_window))):
        frame, objects, invalidated, detected = ns["construct"](subject, window)
        frames[window] = frame
        objects_by_window[window] = objects
        invalidated_by_window[window] = invalidated
        detected_by_window[window] = detected

    requested_objects = objects_by_window[requested_window]
    requested_complete = complete(requested_objects)
    comparator, _ = ns["baseline"](subject)
    matched, requested_only, comparator_only = ns["compare_objects"](
        requested_objects, comparator
    )
    annotation, unmatched = ns["annotation_status"](
        subject, detected_by_window[requested_window]
    )
    if len(requested_only):
        requested_only["excluded_by_ann1"] = requested_only["peak_index"].isin(
            unmatched["ann1"]
        )
        requested_only["excluded_by_ann2"] = requested_only["peak_index"].isin(
            unmatched["ann2"]
        )
        requested_only["excluded_by_both_annotators"] = (
            requested_only["excluded_by_ann1"] & requested_only["excluded_by_ann2"]
        )

    source = ns["load"](subject)["RESP"].astype(float)
    raw_unchanged = frames[requested_window]["respiration"].equals(source)
    valid = frames[requested_window]["respiration_smooth_valid"].eq(True)
    state_count = frames[requested_window].loc[
        valid, ["respiration_rising", "respiration_falling", "respiration_inactive"]
    ].sum(axis=1)
    ordered = requested_complete[
        ["start_index", "peak_index", "end_index"]
    ].dropna()

    requested_objects = requested_objects.copy()
    requested_objects["object_id"] = requested_objects["featuregraph_object_id"].map(
        lambda value: f"bidmc-{subject:02d}-w{requested_window:03d}-{int(value):04d}"
    )
    requested_objects["window_samples"] = requested_window
    requested_only = requested_only.assign(window_samples=requested_window)
    matched = matched.assign(window_samples=requested_window)
    comparator_only = comparator_only.assign(subject=subject, window_samples=requested_window)
    annotation = annotation.assign(window_samples=requested_window)

    per_window = {}
    for window, objects in objects_by_window.items():
        window_complete = complete(objects)
        per_window[window] = {
            "complete_objects": len(window_complete),
            "period_measurements": int(window_complete["period_seconds"].notna().sum()),
            "mean_period_seconds": float(window_complete["period_seconds"].mean()),
            "median_period_seconds": float(window_complete["period_seconds"].median()),
        }

    comparisons = {}
    for left_window, right_window in ((79, requested_window), (requested_window, 100), (79, 100)):
        comparisons[f"{left_window}_to_{right_window}"] = compare_windows(
            ns,
            complete(objects_by_window[left_window]),
            complete(objects_by_window[right_window]),
        )

    summary = {
        "subject": subject,
        "samples": len(frames[requested_window]),
        "detected_peaks": len(detected_by_window[requested_window]),
        "complete_objects": len(requested_complete),
        "period_measurements": int(requested_complete["period_seconds"].notna().sum()),
        "invalidated_complete_objects": len(invalidated_by_window[requested_window]),
        "plateau_ambiguous_objects": int(
            requested_objects["plateau_boundary_ambiguous"].sum()
        ),
        "comparator_objects": len(comparator),
        "matched_objects": len(matched),
        "requested_only_objects": len(requested_only),
        "comparator_only_objects": len(comparator_only),
        "requested_only_excluded_by_both_annotations": int(
            requested_only.get("excluded_by_both_annotators", pd.Series(dtype=bool)).sum()
        ),
        "raw_respiration_unchanged": bool(raw_unchanged),
        "exclusive_exhaustive_states": bool(state_count.eq(1).all()),
        "ordered_complete_boundaries": bool(
            ordered["start_index"].lt(ordered["peak_index"]).all()
            and ordered["peak_index"].lt(ordered["end_index"]).all()
        ),
    }
    for window, values in per_window.items():
        for name, value in values.items():
            summary[f"w{window}_{name}"] = value
    for comparison, values in comparisons.items():
        for name, value in values.items():
            summary[f"w{comparison}_{name}"] = value

    return {
        "summary": summary,
        "objects": requested_objects,
        "matched": matched,
        "requested_only": requested_only,
        "comparator_only": comparator_only,
        "annotation": annotation,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", type=int, default=85)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.window < 2:
        raise ValueError("window must be at least 2 samples")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ns = load_study_namespace()
    contract = {
        "schema_version": 1,
        "execution_id": f"bidmc-respiratory-objects-window-{args.window}-v1",
        "parent_study_id": "bidmc-respiratory-objects",
        "dataset": {
            "name": "BIDMC PPG and Respiration Dataset",
            "version": ns["DATASET_VERSION"],
            "subjects": list(SUBJECTS),
            "sampling_rate_hz": FS,
        },
        "construction": {
            "id": "rolling-envelope-trough-peak-trough-v1",
            "preprocessing": [
                {"operator": "rolling_max", "window_samples": args.window},
                {"operator": "rolling_mean", "window_samples": args.window},
                {"operator": "shift", "samples": -args.window},
            ],
            "effective_support_samples": 2 * args.window - 1,
            "numerical_tolerance": ns["NUMERICAL_ATOL"],
            "states": ["rising", "falling", "inactive"],
            "boundaries": "ordered trough-peak-trough",
            "completeness": "start < peak < end; ordered plateau intervals; not terminal",
        },
        "measurements": [
            "period_seconds",
            "rate_bpm",
            "full_excursion",
            "temporal_symmetry",
        ],
        "comparator": {
            "low_pass_hz": 0.8,
            "peak_distance_samples": 188,
            "peak_prominence": 0.08,
            "matching_tolerance_samples": PAIR_TOLERANCE,
        },
        "registered_comparison_windows": list(REGISTERED_WINDOWS),
        "claim_limits": [
            "Constructed objects are not assumed to be clinically valid breaths.",
            "The result estimates this cohort under this construction, not a universal human average.",
            "Changing the window changes the observational scale and creates a new study version.",
        ],
    }
    contract["contract_sha256"] = value_sha256(contract)
    write_json(output / "study_contract.json", contract, sort_keys=True)

    results: dict[int, dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(run_subject, ns, subject, args.window): subject
            for subject in SUBJECTS
        }
        for future in as_completed(futures):
            subject = futures[future]
            results[subject] = future.result()
            print(f"Completed BIDMC subject {subject:02d}", flush=True)

    ordered = [results[subject] for subject in SUBJECTS]
    subject_summary = pd.DataFrame([item["summary"] for item in ordered])
    objects = pd.concat([item["objects"] for item in ordered], ignore_index=True)
    complete_objects = objects.loc[objects["is_complete"]].copy()
    matched = pd.concat([item["matched"] for item in ordered], ignore_index=True)
    requested_only = pd.concat(
        [item["requested_only"] for item in ordered], ignore_index=True
    )
    comparator_only = pd.concat(
        [item["comparator_only"] for item in ordered], ignore_index=True
    )
    annotation = pd.concat([item["annotation"] for item in ordered], ignore_index=True)

    period = finite_summary(complete_objects["period_seconds"])
    rate = finite_summary(60 / complete_objects["period_seconds"])
    excursion = finite_summary(complete_objects["full_excursion"])
    symmetry = finite_summary(complete_objects["temporal_symmetry"])
    window_rows = []
    for window in sorted(set((*REGISTERED_WINDOWS, args.window))):
        window_rows.append(
            {
                "window_samples": window,
                "effective_support_samples": 2 * window - 1,
                "complete_objects": int(subject_summary[f"w{window}_complete_objects"].sum()),
                "period_measurements": int(subject_summary[f"w{window}_period_measurements"].sum()),
                "mean_period_seconds": float(
                    np.average(
                        subject_summary[f"w{window}_mean_period_seconds"],
                        weights=subject_summary[f"w{window}_period_measurements"],
                    )
                ),
                "median_subject_period_seconds": float(
                    subject_summary[f"w{window}_median_period_seconds"].median()
                ),
            }
        )
    window_summary = pd.DataFrame(window_rows)

    validation_checks = {
        "all_53_subjects_completed": subject_summary["subject"].tolist() == list(SUBJECTS),
        "all_signal_tables_have_60001_rows": bool(subject_summary["samples"].eq(60001).all()),
        "raw_respiration_unchanged": bool(subject_summary["raw_respiration_unchanged"].all()),
        "states_exclusive_and_exhaustive": bool(
            subject_summary["exclusive_exhaustive_states"].all()
        ),
        "complete_boundaries_ordered": bool(
            subject_summary["ordered_complete_boundaries"].all()
        ),
        "all_complete_objects_have_subject_identity": bool(
            complete_objects["subject"].notna().all()
        ),
        "all_measured_periods_are_positive": bool(
            complete_objects["period_seconds"].dropna().gt(0).all()
        ),
        "contract_fingerprint_recorded": len(contract["contract_sha256"]) == 64,
    }
    validation = {
        "all_checks_passed": all(validation_checks.values()),
        "checks": validation_checks,
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
        },
        "contract_sha256": contract["contract_sha256"],
    }
    if not validation["all_checks_passed"]:
        raise AssertionError(validation)

    aggregate = {
        "subjects": len(SUBJECTS),
        "source_observations": int(subject_summary["samples"].sum()),
        "detected_peaks": int(subject_summary["detected_peaks"].sum()),
        "complete_objects": len(complete_objects),
        "period_measurements": period["count"],
        "plateau_ambiguous_objects": int(
            subject_summary["plateau_ambiguous_objects"].sum()
        ),
        "invalidated_complete_objects": int(
            subject_summary["invalidated_complete_objects"].sum()
        ),
        "comparator_objects": int(subject_summary["comparator_objects"].sum()),
        "matched_objects": len(matched),
        "requested_only_objects": len(requested_only),
        "comparator_only_objects": len(comparator_only),
        "requested_only_excluded_by_both_annotations": int(
            requested_only.get("excluded_by_both_annotators", pd.Series(dtype=bool)).sum()
        ),
        "period_seconds": period,
        "rate_bpm": rate,
        "full_excursion": excursion,
        "temporal_symmetry": symmetry,
    }
    write_json(output / "aggregate_results.json", aggregate, sort_keys=True)
    write_json(output / "validation.json", validation, sort_keys=True)

    api_record = {
        "schema_version": "1.0",
        "record_type": "parameterized_measurement",
        "status": "completed",
        "execution_id": contract["execution_id"],
        "study_id": contract["parent_study_id"],
        "construction_id": contract["construction"]["id"],
        "parameters": {
            "window_samples": args.window,
            "sampling_rate_hz": FS,
            "effective_support_samples": 2 * args.window - 1,
            "numerical_tolerance": ns["NUMERICAL_ATOL"],
        },
        "population": {
            "dataset": contract["dataset"]["name"],
            "participants": len(SUBJECTS),
            "complete_objects": len(complete_objects),
            "measured_objects": period["count"],
        },
        "measurements": {
            "period_seconds": period,
            "rate_bpm": rate,
            "full_excursion": excursion,
            "temporal_symmetry": symmetry,
        },
        "validation": validation,
        "claim_limits": contract["claim_limits"],
        "release_projection": {
            "level": "aggregate_parameterized_result",
            "contains_raw_observations": False,
            "contains_direct_identifiers": False,
            "source_terms_apply": True,
        },
    }
    write_json(output / "api_record.json", api_record, sort_keys=True)

    subject_summary.to_csv(output / "subject_summary.csv", index=False)
    window_summary.to_csv(output / "window_summary.csv", index=False)
    objects.to_csv(output / "objects.csv.gz", index=False, compression="gzip")
    complete_objects.to_csv(
        output / "complete_objects.csv.gz", index=False, compression="gzip"
    )
    complete_object_shards = write_csv_shards(
        complete_objects,
        output,
        stem="complete_objects",
    )
    matched.to_csv(output / "matched_objects.csv.gz", index=False, compression="gzip")
    requested_only.to_csv(
        output / f"window_{args.window}_only_objects.csv.gz",
        index=False,
        compression="gzip",
    )
    comparator_only.to_csv(
        output / "comparator_only_objects.csv.gz", index=False, compression="gzip"
    )
    annotation.to_csv(output / "annotation_summary.csv", index=False)

    report = f"""# BIDMC 85-sample respiratory-object study

## Approved change

The rolling-envelope window was changed from the registered 79- and 100-sample
variants to **{args.window} samples**. The dataset, state contract, numerical
tolerance, trough–peak–trough boundaries, completeness rules, comparator,
matching tolerance, measurements, and claim limits were unchanged.

## Result

- Participants: {len(SUBJECTS)}
- Source observations evaluated: {aggregate['source_observations']:,}
- Complete 85-sample objects: {len(complete_objects):,}
- Objects with period measurements: {period['count']:,}
- Mean period: {period['mean']:.4f} seconds
- Median period: {period['median']:.4f} seconds
- Mean object rate: {rate['mean']:.4f} breaths/minute
- Median object rate: {rate['median']:.4f} breaths/minute
- Comparator matches: {len(matched):,}
- 85-sample-only objects relative to the comparator: {len(requested_only):,}
- Comparator-only objects: {len(comparator_only):,}
- All validation checks passed: {validation['all_checks_passed']}

## Interpretation

The mean period is the object-weighted average period of complete BIDMC
respiratory objects produced by this exact 85-sample construction. It is not a
universal estimate of human breathing and does not establish clinical breath
validity.

## Window comparison

{markdown_table(window_summary)}

## Reproduction

```bash
python -m scripts.run_bidmc_parameterized_window_study --window 85
```

The exact declarative contract and its SHA-256 fingerprint are stored in
`study_contract.json`; the public aggregate payload is stored in
`api_record.json`. The complete curated object table is published as
{', '.join(f'`{name}`' for name in complete_object_shards)}.
"""
    (output / "report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
