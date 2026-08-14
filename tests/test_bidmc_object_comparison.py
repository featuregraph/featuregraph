import pandas as pd

from experiments.bidmc_llm_capture.compare_object_tables import (
    comparison_summary,
    match_ordered_objects,
)


def object_table(identifier, peaks):
    return pd.DataFrame(
        {
            identifier: range(len(peaks)),
            "start_index": [peak - 2 for peak in peaks],
            "peak_index": peaks,
            "end_index": [peak + 2 for peak in peaks],
            "is_complete": True,
            "period_seconds": [1.0] * len(peaks),
            "full_excursion": [2.0] * len(peaks),
            "temporal_symmetry": [1.0] * len(peaks),
        }
    )


def test_ordered_matching_preserves_extras_and_errors() -> None:
    featuregraph = object_table(
        "featuregraph_object_id",
        [10, 20, 30],
    )
    llm = object_table("llm_object_id", [11, 29, 50])

    matched, featuregraph_only, llm_only = match_ordered_objects(
        featuregraph,
        llm,
        peak_tolerance_samples=2,
    )
    summary = comparison_summary(matched, featuregraph_only, llm_only)

    assert matched["delta_peak_index"].tolist() == [-1, 1]
    assert featuregraph_only["peak_index"].tolist() == [20]
    assert llm_only["peak_index"].tolist() == [50]
    assert summary["matched_objects"] == 2
    assert summary["featuregraph_complete_objects"] == 3
    assert summary["llm_complete_objects"] == 3
    assert summary["featuregraph_matched_fraction"] == 2 / 3
    assert summary["llm_matched_fraction"] == 2 / 3
    assert summary["median_absolute_peak_index_error"] == 1


def test_incomplete_objects_are_not_matched() -> None:
    featuregraph = object_table("featuregraph_object_id", [10])
    llm = object_table("llm_object_id", [10])
    llm.loc[0, "is_complete"] = False

    matched, featuregraph_only, llm_only = match_ordered_objects(
        featuregraph,
        llm,
        peak_tolerance_samples=2,
    )

    assert matched.empty
    assert len(featuregraph_only) == 1
    assert llm_only.empty

    summary = comparison_summary(matched, featuregraph_only, llm_only)
    assert summary["matched_objects"] == 0
    assert pd.isna(summary["median_absolute_peak_index_error"])
