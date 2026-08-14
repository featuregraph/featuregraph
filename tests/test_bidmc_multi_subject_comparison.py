from pathlib import Path

import pandas as pd

from experiments.bidmc_llm_capture.multi_subject_comparison import (
    annotation_comparison,
    parse_subjects,
)


RESULTS = (
    Path(__file__).parents[1]
    / "experiments"
    / "bidmc_llm_capture"
    / "results"
    / "multi_subject"
)


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
