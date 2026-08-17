from pathlib import Path

import pandas as pd

from experiments.bidmc_llm_capture.multi_subject_comparison import (
    annotation_comparison,
    detector_discordant_episodes,
    native_featuregraph_objects,
    parse_subjects,
    robust_difference_scale,
)

RESULTS = (
    Path(__file__).parents[1]
    / "experiments"
    / "bidmc_llm_capture"
    / "results"
    / "multi_subject"
)
PLATEAU_RESULTS = RESULTS.parent / "envelope_plateau_multi_subject"


def test_parse_subjects_supports_ranges_and_preserves_order() -> None:
    assert parse_subjects("1,3-5,3") == [1, 3, 4, 5]


def test_annotation_comparison_retains_unmatched_peaks() -> None:
    annotations = pd.DataFrame(
        {
            "breaths ann1 [signal sample no]": [11, 199],
            "breaths ann2 [signal sample no]": [10, 350],
        }
    )

    summary, unmatched, detector_only = annotation_comparison(
        [10, 100, 200],
        annotations,
        subject=1,
        method="test",
    )

    assert [row["matched"] for row in summary] == [2, 1]
    assert detector_only["ann1"] == {100}
    assert detector_only["ann2"] == {100, 200}
    assert any(row["kind"] == "reference_only" for row in unmatched)


def test_mad_construction_is_invariant_to_signal_scale() -> None:
    base = pd.DataFrame(
        {
            "subject": [1] * 200,
            "respiration": [
                float((index * index) % 17)
                for index in range(200)
            ],
        }
    )
    scaled = base.copy()
    scaled["respiration"] *= 10

    base_objects, base_peaks = native_featuregraph_objects(
        base,
        scaling="mad",
        normalized_eps=0.5,
    )
    scaled_objects, scaled_peaks = native_featuregraph_objects(
        scaled,
        scaling="mad",
        normalized_eps=0.5,
    )

    assert base_peaks == scaled_peaks
    assert base_objects["peak_index"].equals(
        scaled_objects["peak_index"]
    )
    assert robust_difference_scale(scaled["respiration"]) == (
        10 * robust_difference_scale(base["respiration"])
    )


def test_frozen_multi_subject_results_are_complete_and_accounted() -> None:
    summary = pd.read_csv(RESULTS / "subject_summary.csv")
    matched = pd.concat(
        [
            pd.read_csv(RESULTS / "matched_objects_subjects_01_27.csv"),
            pd.read_csv(RESULTS / "matched_objects_subjects_28_53.csv"),
        ],
        ignore_index=True,
    )

    assert summary["subject"].astype(int).tolist() == list(range(1, 54))
    assert len(matched) == 6200
    assert matched["delta_peak_index"].abs().le(63).all()
    assert (
        summary["matched_objects"] + summary["featuregraph_only_objects"]
        == summary["featuregraph_complete_objects"]
    ).all()
    assert (
        summary["matched_objects"] + summary["llm_only_objects"]
        == summary["llm_complete_objects"]
    ).all()


def test_detector_discordant_handoff_labels_runs_without_clinical_claims() -> None:
    objects = pd.DataFrame(
        {
            "subject": [2, 2, 2],
            "featuregraph_object_id": [10, 11, 14],
            "start_index": [100, 200, 400],
            "peak_index": [125, 225, 425],
            "end_index": [150, 250, 450],
            "peak_detection_index": [225, 325, 525],
            "peak_detection_latency_samples": [100, 100, 100],
            "peak_detection_latency_seconds": [0.8, 0.8, 0.8],
            "period_seconds": [1.0, 1.0, 2.0],
            "full_excursion": [0.5, 0.6, 0.7],
            "temporal_symmetry": [1.0, 1.0, 1.0],
            "excluded_by_ann1": [True, False, False],
            "excluded_by_ann2": [True, False, True],
            "excluded_by_both_annotators": [True, False, False],
            "plateau_boundary_ambiguous": [False, False, False],
        }
    )

    episodes = detector_discordant_episodes(objects)

    assert episodes["temporal_pattern"].tolist() == [
        "burst",
        "burst",
        "isolated",
    ]
    assert episodes["burst_size"].tolist() == [2, 2, 1]
    assert episodes["annotation_status"].tolist() == [
        "excluded_by_both",
        "retained_by_both",
        "excluded_by_ann2",
    ]
    assert episodes["clinical_interpretation"].eq("unassigned").all()


def test_plateau_beta_results_are_complete_and_accounted() -> None:
    cohort = pd.read_csv(PLATEAU_RESULTS / "cohort_summary.csv")
    handoff = pd.read_csv(
        PLATEAU_RESULTS / "detector_discordant_episodes.csv"
    )
    all_subjects = cohort.loc[cohort["cohort"].eq("all_subjects")].iloc[0]

    assert int(all_subjects["featuregraph_complete_objects"]) == 8133
    assert int(all_subjects["matched_objects"]) == 7086
    assert int(all_subjects["featuregraph_only_objects"]) == 1047
    assert int(all_subjects["baseline_only_objects"]) == 82
    assert int(all_subjects["featuregraph_ambiguous_objects"]) == 100
    assert int(
        all_subjects["featuregraph_invalidated_complete_objects"]
    ) == 47
    assert len(handoff) == 1047
    assert handoff["clinical_interpretation"].eq("unassigned").all()
