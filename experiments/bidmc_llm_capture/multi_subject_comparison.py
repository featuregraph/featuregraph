"""Run the frozen BIDMC comparison across all available subjects."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

import featuregraph as fg
from experiments.bidmc_llm_capture.compare_object_tables import (
    comparison_summary,
    match_ordered_objects,
    optimal_ordered_pairs,
)
from experiments.bidmc_llm_capture.native_envelope import (
    native_envelope_objects,
)
from experiments.bidmc_llm_capture.prepare_blinded_trial import (
    DIFF_LAG,
    EPS,
    MAX_STATE_GAP,
    SAMPLING_RATE,
)
from experiments.bidmc_llm_capture.reproduce_llm_method import (
    detect_boundaries,
    reproduce,
)

PEAK_TOLERANCE_SAMPLES = 63
ANNOTATION_COLUMNS = (
    "breaths ann1 [signal sample no]",
    "breaths ann2 [signal sample no]",
)
CONSTRUCTION_VERSION = "envelope_plateau_v1"


def robust_difference_scale(
    signal: pd.Series,
    *,
    lag: int = DIFF_LAG,
) -> float:
    """Return the median absolute deviation of a lagged difference."""
    difference = signal.diff(lag)
    median = difference.median()
    return float((difference - median).abs().median())


@lru_cache(maxsize=1)
def normalized_entry_threshold() -> float:
    """Calibrate the dimensionless threshold once from subject 1."""
    reference = fg.datasets.bidmc(subject=1)
    scale = robust_difference_scale(reference["respiration"])
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("Subject 1 difference MAD must be positive.")
    return EPS / scale


def native_featuregraph_objects(
    observations: pd.DataFrame,
    *,
    construction: str = "difference",
    scaling: str = "absolute",
    normalized_eps: float | None = None,
) -> tuple[pd.DataFrame, list[int]]:
    """Apply a native construction and return objects and detected peaks."""
    if construction in {"envelope", "envelope_plateau"}:
        return native_envelope_objects(
            observations,
            plateau_midpoints=construction == "envelope_plateau",
        )
    if construction != "difference":
        raise ValueError(
            "construction must be 'difference', 'envelope', or "
            "'envelope_plateau'"
        )
    if scaling not in {"absolute", "mad"}:
        raise ValueError("scaling must be 'absolute' or 'mad'")

    signal = "respiration"
    eps = EPS
    amplitude_scale = 1.0
    if scaling == "mad":
        amplitude_scale = robust_difference_scale(
            observations["respiration"]
        )
        if not np.isfinite(amplitude_scale) or amplitude_scale <= 0:
            raise ValueError("Each subject difference MAD must be positive.")
        observations = observations.copy()
        signal = "respiration_scaled"
        observations[signal] = (
            observations["respiration"] / amplitude_scale
        )
        eps = (
            normalized_entry_threshold()
            if normalized_eps is None
            else normalized_eps
        )

    behavior = fg.oscillation.Oscillation(
        signals=signal,
        group="subject",
        smooth_signal=False,
        diff_lag=DIFF_LAG,
        eps=eps,
        max_state_gap=MAX_STATE_GAP,
    )
    features = behavior.fit_transform(observations)
    objects = behavior.summarize(
        features,
        signal=signal,
        include_partial=True,
    ).table.copy()
    objects["period_seconds"] = objects["period"] / SAMPLING_RATE
    objects["full_excursion"] = (
        2 * objects["amplitude"] * amplitude_scale
    )
    objects = objects[
        [
            "oscillation_id",
            "start_index",
            "peak_index",
            "end_index",
            "is_complete",
            "period_seconds",
            "full_excursion",
            "temporal_symmetry",
        ]
    ].rename(columns={"oscillation_id": "featuregraph_object_id"})
    detected_peaks = features.index[
        features[f"{signal}_peak"]
    ].astype(int).tolist()
    return objects, detected_peaks


def annotation_comparison(
    detected: list[int],
    annotations: pd.DataFrame,
    *,
    subject: int,
    method: str,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, set[int]],
]:
    """Compare one detector with both annotators under the frozen tolerance."""
    summary_rows: list[dict[str, object]] = []
    unmatched_rows: list[dict[str, object]] = []
    unmatched_detected: dict[str, set[int]] = {}

    for column in ANNOTATION_COLUMNS:
        annotator = column.split()[1]
        reference = (
            annotations[column].dropna().astype(int).sort_values().tolist()
        )
        pairs = optimal_ordered_pairs(
            detected,
            reference,
            tolerance=PEAK_TOLERANCE_SAMPLES,
        )
        detected_indices = {pair[0] for pair in pairs}
        reference_indices = {pair[1] for pair in pairs}
        distances = [
            abs(detected[left] - reference[right]) for left, right in pairs
        ]
        detector_only = {
            detected[index]
            for index in range(len(detected))
            if index not in detected_indices
        }
        unmatched_detected[annotator] = detector_only
        summary_rows.append(
            {
                "subject": subject,
                "method": method,
                "annotator": annotator,
                "detected_peaks": len(detected),
                "reference_peaks": len(reference),
                "matched": len(pairs),
                "detector_only": len(detector_only),
                "reference_only": len(reference) - len(reference_indices),
                "matched_fraction_detected": (
                    len(pairs) / len(detected) if detected else np.nan
                ),
                "matched_fraction_reference": (
                    len(pairs) / len(reference) if reference else np.nan
                ),
                "median_absolute_error_samples": (
                    float(np.median(distances)) if distances else np.nan
                ),
                "maximum_absolute_error_samples": (
                    max(distances) if distances else np.nan
                ),
            }
        )
        unmatched_rows.extend(
            {
                "subject": subject,
                "method": method,
                "annotator": annotator,
                "kind": "detector_only",
                "peak_index": peak,
            }
            for peak in sorted(detector_only)
        )
        unmatched_rows.extend(
            {
                "subject": subject,
                "method": method,
                "annotator": annotator,
                "kind": "reference_only",
                "peak_index": reference[index],
            }
            for index in range(len(reference))
            if index not in reference_indices
        )
    return summary_rows, unmatched_rows, unmatched_detected


def compare_subject(
    subject: int,
    scaling: str = "absolute",
    construction: str = "difference",
) -> dict[str, pd.DataFrame | pd.Series]:
    """Run both frozen paths and annotation checks for one subject."""
    observations = fg.datasets.bidmc(subject=subject)
    annotations = fg.datasets.bidmc_breaths(subject=subject)

    featuregraph_objects, featuregraph_peaks = native_featuregraph_objects(
        observations,
        construction=construction,
        scaling=scaling,
    )
    if "plateau_boundary_ambiguous" in featuregraph_objects:
        featuregraph_ambiguous = featuregraph_objects.loc[
            featuregraph_objects["plateau_boundary_ambiguous"]
        ].copy()
    else:
        featuregraph_ambiguous = pd.DataFrame()
    raw = observations[["respiration"]].copy()
    llm_objects = reproduce(raw)
    llm_peaks, _ = detect_boundaries(raw["respiration"].to_numpy())
    llm_peak_list = llm_peaks.astype(int).tolist()

    matched, featuregraph_only, llm_only = match_ordered_objects(
        featuregraph_objects,
        llm_objects,
        peak_tolerance_samples=PEAK_TOLERANCE_SAMPLES,
    )
    summary = comparison_summary(matched, featuregraph_only, llm_only)
    summary["subject"] = subject
    summary["featuregraph_construction"] = construction
    summary["featuregraph_scaling"] = scaling
    summary["samples"] = len(observations)
    summary["featuregraph_detected_peaks"] = len(featuregraph_peaks)
    summary["llm_detected_peaks"] = len(llm_peak_list)
    summary["featuregraph_partial_objects"] = int(
        (~featuregraph_objects["is_complete"]).sum()
    )
    summary["featuregraph_ambiguous_objects"] = len(
        featuregraph_ambiguous
    )
    summary["featuregraph_invalidated_complete_objects"] = int(
        featuregraph_ambiguous.get(
            "plateau_invalidated_complete",
            pd.Series(dtype=bool),
        ).sum()
    )
    summary["llm_partial_objects"] = int(
        (~llm_objects["is_complete"]).sum()
    )
    for column in (
        "start_index",
        "peak_index",
        "end_index",
        "period_seconds",
        "full_excursion",
        "temporal_symmetry",
    ):
        summary[f"median_signed_{column}_difference"] = (
            matched[f"delta_{column}"].median() if len(matched) else np.nan
        )

    annotation_rows: list[dict[str, object]] = []
    annotation_unmatched: list[dict[str, object]] = []
    fg_annotation_extras: dict[str, set[int]] = {}
    for method, peaks in (
        ("featuregraph", featuregraph_peaks),
        ("llm_selected_baseline", llm_peak_list),
    ):
        rows, unmatched, detector_only = annotation_comparison(
            peaks,
            annotations,
            subject=subject,
            method=method,
        )
        annotation_rows.extend(rows)
        annotation_unmatched.extend(unmatched)
        if method == "featuregraph":
            fg_annotation_extras = detector_only

    featuregraph_only = featuregraph_only.copy()
    if len(featuregraph_only):
        featuregraph_only["excluded_by_ann1"] = featuregraph_only[
            "peak_index"
        ].isin(fg_annotation_extras["ann1"])
        featuregraph_only["excluded_by_ann2"] = featuregraph_only[
            "peak_index"
        ].isin(fg_annotation_extras["ann2"])
        featuregraph_only["excluded_by_both_annotators"] = (
            featuregraph_only["excluded_by_ann1"]
            & featuregraph_only["excluded_by_ann2"]
        )
        summary["featuregraph_only_excluded_by_both_annotators"] = int(
            featuregraph_only["excluded_by_both_annotators"].sum()
        )
    else:
        summary["featuregraph_only_excluded_by_both_annotators"] = 0

    for table in (
        matched,
        featuregraph_only,
        llm_only,
        featuregraph_ambiguous,
    ):
        table.insert(0, "subject", subject)

    return {
        "summary": summary,
        "matched": matched,
        "featuregraph_only": featuregraph_only,
        "featuregraph_ambiguous": featuregraph_ambiguous,
        "llm_only": llm_only,
        "annotation_summary": pd.DataFrame(annotation_rows),
        "annotation_unmatched": pd.DataFrame(annotation_unmatched),
    }


def cohort_summary(
    subject_summary: pd.DataFrame,
    matched: pd.DataFrame,
    featuregraph_only: pd.DataFrame,
    annotation_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate the full and held-out cohorts from saved object rows."""
    rows: list[dict[str, object]] = []
    cohorts = {
        "all_subjects": set(subject_summary["subject"]),
        "transfer_subjects_02_53": set(
            subject_summary.loc[subject_summary["subject"] != 1, "subject"]
        ),
    }
    for cohort, subject_ids in cohorts.items():
        subjects = subject_summary[
            subject_summary["subject"].isin(subject_ids)
        ]
        pairs = matched[matched["subject"].isin(subject_ids)]
        if "subject" in featuregraph_only:
            native_only = featuregraph_only[
                featuregraph_only["subject"].isin(subject_ids)
            ]
        else:
            native_only = pd.DataFrame(
                columns=["excluded_by_both_annotators"]
            )
        annotations = annotation_summary[
            annotation_summary["subject"].isin(subject_ids)
        ]
        row: dict[str, object] = {
            "cohort": cohort,
            "subjects": len(subjects),
            "featuregraph_complete_objects": int(
                subjects["featuregraph_complete_objects"].sum()
            ),
            "baseline_complete_objects": int(
                subjects["llm_complete_objects"].sum()
            ),
            "matched_objects": int(subjects["matched_objects"].sum()),
            "featuregraph_only_objects": int(
                subjects["featuregraph_only_objects"].sum()
            ),
            "baseline_only_objects": int(
                subjects["llm_only_objects"].sum()
            ),
            "featuregraph_ambiguous_objects": int(
                subjects["featuregraph_ambiguous_objects"].sum()
            ),
            "featuregraph_invalidated_complete_objects": int(
                subjects[
                    "featuregraph_invalidated_complete_objects"
                ].sum()
            ),
            "median_subject_featuregraph_matched_fraction": subjects[
                "featuregraph_matched_fraction"
            ].median(),
            "median_subject_baseline_matched_fraction": subjects[
                "llm_matched_fraction"
            ].median(),
            "median_absolute_peak_error_samples": pairs[
                "delta_peak_index"
            ].abs().median(),
            "p90_absolute_peak_error_samples": pairs[
                "delta_peak_index"
            ].abs().quantile(0.9),
            "median_absolute_period_error_seconds": pairs[
                "delta_period_seconds"
            ].abs().median(),
            "median_absolute_full_excursion_error": pairs[
                "delta_full_excursion"
            ].abs().median(),
            "median_absolute_temporal_symmetry_error": pairs[
                "delta_temporal_symmetry"
            ].abs().median(),
            "featuregraph_only_excluded_by_both_annotators": int(
                native_only["excluded_by_both_annotators"].sum()
            ),
            "featuregraph_only_excluded_by_both_fraction": native_only[
                "excluded_by_both_annotators"
            ].mean(),
        }
        for method in ("featuregraph", "llm_selected_baseline"):
            for annotator in ("ann1", "ann2"):
                selection = annotations[
                    (annotations["method"] == method)
                    & (annotations["annotator"] == annotator)
                ]
                prefix = f"{method}_{annotator}"
                matched_count = selection["matched"].sum()
                row[f"{prefix}_detected_matched_fraction"] = (
                    matched_count / selection["detected_peaks"].sum()
                )
                row[f"{prefix}_reference_matched_fraction"] = (
                    matched_count / selection["reference_peaks"].sum()
                )
        rows.append(row)
    return pd.DataFrame(rows)


def detector_discordant_episodes(
    featuregraph_only: pd.DataFrame,
) -> pd.DataFrame:
    """Build the stable handoff table for unmatched FeatureGraph objects.

    Labels in this table describe computational disagreement and temporal
    organization only. ``clinical_interpretation`` is deliberately left
    unassigned for downstream domain review.
    """
    episodes = featuregraph_only.copy()
    if episodes.empty:
        return episodes

    episodes = episodes.sort_values(
        ["subject", "featuregraph_object_id"],
        kind="stable",
    ).reset_index(drop=True)
    subject = episodes["subject"].astype(int)
    object_id = episodes["featuregraph_object_id"].astype(int)
    new_run = subject.ne(subject.shift()) | object_id.diff().ne(1)
    episodes["burst_number"] = (
        new_run.groupby(subject, sort=False).cumsum().astype(int)
    )
    group_columns = ["subject", "burst_number"]
    episodes["burst_size"] = episodes.groupby(
        group_columns,
        sort=False,
    )["featuregraph_object_id"].transform("size")
    episodes["temporal_pattern"] = np.where(
        episodes["burst_size"].gt(1),
        "burst",
        "isolated",
    )
    episodes["episode_id"] = [
        f"bidmc-{subject_id:02d}-fg-{candidate_id:04d}"
        for subject_id, candidate_id in zip(subject, object_id, strict=True)
    ]
    episodes["burst_id"] = [
        f"bidmc-{subject_id:02d}-burst-{burst_id:03d}"
        for subject_id, burst_id in zip(
            subject,
            episodes["burst_number"],
            strict=True,
        )
    ]
    episodes["previous_featuregraph_object_id"] = object_id - 1
    episodes["next_featuregraph_object_id"] = object_id + 1

    episodes["discordance_type"] = "featuregraph_only"
    ann1 = episodes["excluded_by_ann1"].astype(bool)
    ann2 = episodes["excluded_by_ann2"].astype(bool)
    episodes["annotation_status"] = np.select(
        [ann1 & ann2, ann1 & ~ann2, ~ann1 & ann2],
        ["excluded_by_both", "excluded_by_ann1", "excluded_by_ann2"],
        default="retained_by_both",
    )
    episodes["retained_by_one_or_both_annotators"] = ~(ann1 & ann2)
    episodes["clinical_interpretation"] = "unassigned"

    for boundary in ("start", "peak", "end"):
        episodes[f"{boundary}_time_seconds"] = (
            episodes[f"{boundary}_index"] / SAMPLING_RATE
        )
    episodes["peak_detection_time_seconds"] = (
        episodes["peak_detection_index"] / SAMPLING_RATE
    )
    episodes["sampling_rate_hz"] = SAMPLING_RATE
    episodes["construction"] = "envelope_plateau"
    episodes["construction_version"] = CONSTRUCTION_VERSION
    episodes["comparator"] = "frozen_llm_scipy_find_peaks"

    leading_columns = [
        "episode_id",
        "subject",
        "featuregraph_object_id",
        "discordance_type",
        "temporal_pattern",
        "burst_id",
        "burst_size",
        "previous_featuregraph_object_id",
        "next_featuregraph_object_id",
        "start_index",
        "start_time_seconds",
        "peak_index",
        "peak_time_seconds",
        "end_index",
        "end_time_seconds",
        "peak_detection_index",
        "peak_detection_time_seconds",
        "peak_detection_latency_samples",
        "peak_detection_latency_seconds",
        "period_seconds",
        "full_excursion",
        "temporal_symmetry",
        "annotation_status",
        "excluded_by_ann1",
        "excluded_by_ann2",
        "excluded_by_both_annotators",
        "retained_by_one_or_both_annotators",
        "plateau_boundary_ambiguous",
        "clinical_interpretation",
        "sampling_rate_hz",
        "construction",
        "construction_version",
        "comparator",
    ]
    remaining_columns = [
        column for column in episodes if column not in leading_columns
    ]
    return episodes[leading_columns + remaining_columns]


def run(
    subjects: list[int],
    output_directory: Path,
    *,
    jobs: int = 1,
    scaling: str = "absolute",
    construction: str = "difference",
) -> None:
    """Run a declared subject cohort and save all audit tables."""
    output_directory.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, object]] = []
    if jobs == 1:
        results = []
        for subject in subjects:
            print(f"Comparing BIDMC subject {subject:02d}...", flush=True)
            try:
                results.append(
                    compare_subject(
                        subject,
                        scaling,
                        construction,
                    )
                )
            except ValueError as error:
                failures.append(
                    {"subject": subject, "error": str(error)}
                )
                print(
                    f"Skipped BIDMC subject {subject:02d}: {error}",
                    flush=True,
                )
    else:
        result_by_subject = {}
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            futures = {
                executor.submit(
                    compare_subject,
                    subject,
                    scaling,
                    construction,
                ): subject
                for subject in subjects
            }
            for future in as_completed(futures):
                subject = futures[future]
                try:
                    result_by_subject[subject] = future.result()
                    print(
                        f"Completed BIDMC subject {subject:02d}.",
                        flush=True,
                    )
                except ValueError as error:
                    failures.append(
                        {"subject": subject, "error": str(error)}
                    )
                    print(
                        f"Skipped BIDMC subject {subject:02d}: {error}",
                        flush=True,
                    )
        results = [
            result_by_subject[subject]
            for subject in subjects
            if subject in result_by_subject
        ]

    pd.DataFrame(
        failures,
        columns=["subject", "error"],
    ).to_csv(output_directory / "failures.csv", index=False)

    summary = pd.DataFrame([result["summary"] for result in results])
    ordered = ["subject"] + [column for column in summary if column != "subject"]
    summary = summary[ordered]
    summary.to_csv(output_directory / "subject_summary.csv", index=False)

    outputs = {
        "featuregraph_only_objects.csv": "featuregraph_only",
        "plateau_ambiguous_objects.csv": "featuregraph_ambiguous",
        "llm_only_objects.csv": "llm_only",
        "annotation_summary.csv": "annotation_summary",
        "annotation_unmatched_peaks.csv": "annotation_unmatched",
    }
    combined_outputs = {}
    for filename, key in outputs.items():
        frames = [result[key] for result in results if len(result[key])]
        combined = (
            pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        )
        combined.to_csv(output_directory / filename, index=False)
        combined_outputs[key] = combined

    matched_frames = [result["matched"] for result in results]
    matched_objects = pd.concat(matched_frames, ignore_index=True)
    for start, end in ((1, 27), (28, 53)):
        selection = matched_objects["subject"].between(start, end)
        matched_objects.loc[selection].to_csv(
            output_directory
            / f"matched_objects_subjects_{start:02d}_{end:02d}.csv",
            index=False,
        )
    combined_outputs["matched"] = matched_objects

    detector_discordant_episodes(
        combined_outputs["featuregraph_only"]
    ).to_csv(
        output_directory / "detector_discordant_episodes.csv",
        index=False,
    )

    cohort_summary(
        summary,
        combined_outputs["matched"],
        combined_outputs["featuregraph_only"],
        combined_outputs["annotation_summary"],
    ).to_csv(output_directory / "cohort_summary.csv", index=False)

    print(
        f"Wrote {len(results)} subject comparisons and "
        f"{len(failures)} failures to {output_directory}"
    )


def parse_subjects(value: str) -> list[int]:
    """Parse comma-separated subject numbers and inclusive ranges."""
    subjects: list[int] = []
    for item in value.split(","):
        if "-" in item:
            start, end = (int(part) for part in item.split("-", maxsplit=1))
            subjects.extend(range(start, end + 1))
        else:
            subjects.append(int(item))
    if not subjects or any(subject < 1 or subject > 53 for subject in subjects):
        raise ValueError("subjects must be between 1 and 53")
    return list(dict.fromkeys(subjects))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subjects", default="1-53")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument(
        "--scaling",
        choices=("absolute", "mad"),
        default="absolute",
    )
    parser.add_argument(
        "--construction",
        choices=("difference", "envelope", "envelope_plateau"),
        default="difference",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=(Path(__file__).parent / "results" / "multi_subject"),
    )
    arguments = parser.parse_args()
    run(
        parse_subjects(arguments.subjects),
        arguments.output_directory,
        jobs=arguments.jobs,
        scaling=arguments.scaling,
        construction=arguments.construction,
    )
