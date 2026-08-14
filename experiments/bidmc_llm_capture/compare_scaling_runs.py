"""Compare absolute and MAD-normalized BIDMC cohort results."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent / "results"
ABSOLUTE = ROOT / "multi_subject"
MAD = ROOT / "mad_multi_subject"


def read_matched(directory: Path) -> pd.DataFrame:
    return pd.concat(
        [
            pd.read_csv(directory / "matched_objects_subjects_01_27.csv"),
            pd.read_csv(directory / "matched_objects_subjects_28_53.csv"),
        ],
        ignore_index=True,
    )


def summarize_run(
    label: str,
    directory: Path,
    common_subjects: set[int],
) -> dict[str, object]:
    subjects = pd.read_csv(directory / "subject_summary.csv")
    subjects = subjects.loc[subjects["subject"].isin(common_subjects)]
    matched = read_matched(directory)
    matched = matched.loc[matched["subject"].isin(common_subjects)]
    annotations = pd.read_csv(directory / "annotation_summary.csv")
    annotations = annotations.loc[
        (annotations["subject"].isin(common_subjects))
        & annotations["method"].eq("featuregraph")
    ]

    native_count = int(subjects["featuregraph_complete_objects"].sum())
    baseline_count = int(subjects["llm_complete_objects"].sum())
    matched_count = int(subjects["matched_objects"].sum())
    row: dict[str, object] = {
        "construction": label,
        "subjects": len(subjects),
        "featuregraph_complete_objects": native_count,
        "baseline_complete_objects": baseline_count,
        "matched_objects": matched_count,
        "featuregraph_only_objects": int(
            subjects["featuregraph_only_objects"].sum()
        ),
        "baseline_only_objects": int(subjects["llm_only_objects"].sum()),
        "featuregraph_matched_fraction": matched_count / native_count,
        "baseline_matched_fraction": matched_count / baseline_count,
        "median_subject_featuregraph_matched_fraction": subjects[
            "featuregraph_matched_fraction"
        ].median(),
        "median_subject_baseline_matched_fraction": subjects[
            "llm_matched_fraction"
        ].median(),
        "median_subject_absolute_count_error": (
            subjects["featuregraph_complete_objects"]
            - subjects["llm_complete_objects"]
        ).abs().median(),
        "subjects_over_baseline_count": int(
            (
                subjects["featuregraph_complete_objects"]
                > subjects["llm_complete_objects"]
            ).sum()
        ),
        "subjects_under_baseline_count": int(
            (
                subjects["featuregraph_complete_objects"]
                < subjects["llm_complete_objects"]
            ).sum()
        ),
        "median_absolute_peak_error_samples": matched[
            "delta_peak_index"
        ].abs().median(),
        "p90_absolute_peak_error_samples": matched[
            "delta_peak_index"
        ].abs().quantile(0.9),
        "median_absolute_period_error_seconds": matched[
            "delta_period_seconds"
        ].abs().median(),
        "median_absolute_full_excursion_error": matched[
            "delta_full_excursion"
        ].abs().median(),
        "median_absolute_temporal_symmetry_error": matched[
            "delta_temporal_symmetry"
        ].abs().median(),
    }

    for annotator in ("ann1", "ann2"):
        selected = annotations.loc[annotations["annotator"].eq(annotator)]
        annotation_matches = selected["matched"].sum()
        row[f"{annotator}_detected_matched_fraction"] = (
            annotation_matches / selected["detected_peaks"].sum()
        )
        row[f"{annotator}_reference_matched_fraction"] = (
            annotation_matches / selected["reference_peaks"].sum()
        )
    return row


def main() -> None:
    absolute_subjects = pd.read_csv(ABSOLUTE / "subject_summary.csv")
    mad_subjects = pd.read_csv(MAD / "subject_summary.csv")
    common_subjects = set(mad_subjects["subject"].astype(int))

    comparison = pd.DataFrame(
        [
            summarize_run("absolute", ABSOLUTE, common_subjects),
            summarize_run("mad", MAD, common_subjects),
        ]
    )
    comparison.to_csv(MAD / "scaling_comparison.csv", index=False)

    paired = absolute_subjects.merge(
        mad_subjects,
        on="subject",
        suffixes=("_absolute", "_mad"),
    )
    for column in (
        "featuregraph_complete_objects",
        "matched_objects",
        "featuregraph_only_objects",
        "llm_only_objects",
        "featuregraph_matched_fraction",
        "llm_matched_fraction",
    ):
        paired[f"delta_{column}"] = (
            paired[f"{column}_mad"] - paired[f"{column}_absolute"]
        )
    paired.to_csv(MAD / "subject_scaling_deltas.csv", index=False)

    failures = pd.read_csv(MAD / "failures.csv")
    failed_absolute = absolute_subjects.loc[
        absolute_subjects["subject"].isin(failures["subject"]),
        [
            "subject",
            "featuregraph_complete_objects",
            "llm_complete_objects",
            "matched_objects",
            "featuregraph_only_objects",
            "llm_only_objects",
        ],
    ]
    failed_absolute.to_csv(
        MAD / "absolute_results_for_mad_failures.csv",
        index=False,
    )

    print(comparison.to_string(index=False))
    print("\nMAD failures under the original absolute construction:")
    print(failed_absolute.to_string(index=False))


if __name__ == "__main__":
    main()
