"""Compare frozen FeatureGraph and blinded-LLM respiration objects."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


BOUNDARY_COLUMNS = ("start_index", "peak_index", "end_index")
PROPERTY_COLUMNS = (
    "period_seconds",
    "full_excursion",
    "temporal_symmetry",
)


def match_ordered_objects(
    featuregraph: pd.DataFrame,
    llm: pd.DataFrame,
    *,
    peak_tolerance_samples: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Match complete objects in peak order, once each, within tolerance."""
    left = (
        featuregraph.loc[featuregraph["is_complete"]]
        .sort_values("peak_index")
        .reset_index(drop=True)
    )
    right = (
        llm.loc[llm["is_complete"]]
        .sort_values("peak_index")
        .reset_index(drop=True)
    )
    left_index = right_index = 0
    pairs: list[dict[str, object]] = []
    matched_left: set[int] = set()
    matched_right: set[int] = set()

    while left_index < len(left) and right_index < len(right):
        left_peak = int(left.at[left_index, "peak_index"])
        right_peak = int(right.at[right_index, "peak_index"])
        offset = left_peak - right_peak

        if abs(offset) <= peak_tolerance_samples:
            row: dict[str, object] = {
                "featuregraph_object_id": left.at[
                    left_index,
                    "featuregraph_object_id",
                ],
                "llm_object_id": right.at[right_index, "llm_object_id"],
            }
            for column in (*BOUNDARY_COLUMNS, *PROPERTY_COLUMNS):
                row[f"featuregraph_{column}"] = left.at[left_index, column]
                row[f"llm_{column}"] = right.at[right_index, column]
                row[f"delta_{column}"] = (
                    left.at[left_index, column]
                    - right.at[right_index, column]
                )
            pairs.append(row)
            matched_left.add(left_index)
            matched_right.add(right_index)
            left_index += 1
            right_index += 1
        elif left_peak < right_peak:
            left_index += 1
        else:
            right_index += 1

    matched = pd.DataFrame(pairs)
    featuregraph_only = left.loc[
        ~left.index.isin(matched_left)
    ].reset_index(drop=True)
    llm_only = right.loc[
        ~right.index.isin(matched_right)
    ].reset_index(drop=True)
    return matched, featuregraph_only, llm_only


def comparison_summary(
    matched: pd.DataFrame,
    featuregraph_only: pd.DataFrame,
    llm_only: pd.DataFrame,
) -> pd.Series:
    """Summarize object agreement without hiding unmatched objects."""
    summary: dict[str, float | int] = {
        "matched_objects": len(matched),
        "featuregraph_only_objects": len(featuregraph_only),
        "llm_only_objects": len(llm_only),
        "featuregraph_complete_objects": (
            len(matched) + len(featuregraph_only)
        ),
        "llm_complete_objects": len(matched) + len(llm_only),
    }
    summary["featuregraph_matched_fraction"] = (
        len(matched) / summary["featuregraph_complete_objects"]
        if summary["featuregraph_complete_objects"]
        else float("nan")
    )
    summary["llm_matched_fraction"] = (
        len(matched) / summary["llm_complete_objects"]
        if summary["llm_complete_objects"]
        else float("nan")
    )
    for column in (*BOUNDARY_COLUMNS, *PROPERTY_COLUMNS):
        delta_column = f"delta_{column}"
        delta = (
            matched[delta_column].abs()
            if delta_column in matched
            else pd.Series(dtype=float)
        )
        summary[f"median_absolute_{column}_error"] = delta.median()
        summary[f"maximum_absolute_{column}_error"] = delta.max()
    for column in PROPERTY_COLUMNS:
        summary[f"featuregraph_mean_{column}"] = (
            matched[f"featuregraph_{column}"].mean()
            if f"featuregraph_{column}" in matched
            else float("nan")
        )
        summary[f"llm_mean_{column}"] = (
            matched[f"llm_{column}"].mean()
            if f"llm_{column}" in matched
            else float("nan")
        )
    return pd.Series(summary)


def compare(directory: Path, peak_tolerance_samples: int = 63) -> None:
    """Read both tables and write matched, unmatched, and summary outputs."""
    featuregraph = pd.read_csv(
        directory / "featuregraph_objects_subject_01.csv"
    )
    llm = pd.read_csv(directory / "llm_objects_subject_01.csv")
    matched, featuregraph_only, llm_only = match_ordered_objects(
        featuregraph,
        llm,
        peak_tolerance_samples=peak_tolerance_samples,
    )
    matched.to_csv(directory / "matched_objects.csv", index=False)
    featuregraph_only.to_csv(
        directory / "featuregraph_only_objects.csv",
        index=False,
    )
    llm_only.to_csv(directory / "llm_only_objects.csv", index=False)
    summary = comparison_summary(matched, featuregraph_only, llm_only)
    summary.rename("value").to_csv(directory / "comparison_summary.csv")
    print(summary.to_string())


if __name__ == "__main__":
    compare(Path(__file__).parent / "generated")
