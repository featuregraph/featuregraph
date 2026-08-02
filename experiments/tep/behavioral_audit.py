"""Audit behavioral changes in Tennessee Eastman oscillation objects.

This experiment deliberately avoids predictive models. It characterizes how
object properties change after a known fault injection, measures whether those
changes repeat across complete simulation runs, and executes a catalog of
deterministic questions against the resulting object table.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from experiments.tep.compare_faults import FEATUREGRAPH_FEATURES


REGIMES = ("early_response", "post_response")
CONSISTENCY_THRESHOLD = 0.80
CLIFFS_DELTA_THRESHOLD = 0.33


def cliffs_delta(reference: pd.Series, comparison: pd.Series) -> float:
    """Return the signed probability-of-superiority effect size.

    Positive values mean that comparison observations tend to be larger than
    reference observations. Ties contribute zero.
    """
    reference_values = reference.dropna().to_numpy(dtype=float)
    comparison_values = comparison.dropna().to_numpy(dtype=float)
    if not len(reference_values) or not len(comparison_values):
        return np.nan
    differences = comparison_values[:, None] - reference_values[None, :]
    return float((np.count_nonzero(differences > 0) - np.count_nonzero(
        differences < 0
    )) / differences.size)


def characterize_regimes(
    objects: pd.DataFrame,
    *,
    properties: tuple[str, ...] = FEATUREGRAPH_FEATURES,
) -> pd.DataFrame:
    """Compare each post-injection regime with its run-specific baseline."""
    required = {
        "fault_number",
        "simulation_run",
        "regime",
        *properties,
    }
    missing = required - set(objects)
    if missing:
        raise ValueError(f"missing object columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    group_columns = ["fault_number", "simulation_run"]
    for (fault_number, simulation_run), run in objects.groupby(
        group_columns, sort=True
    ):
        baseline = run.loc[run["regime"].eq("pre_injection")]
        if baseline.empty:
            continue
        for regime in REGIMES:
            comparison = run.loc[run["regime"].eq(regime)]
            if comparison.empty:
                continue
            for property_name in properties:
                reference = baseline[property_name]
                changed = comparison[property_name]
                baseline_median = float(reference.median())
                regime_median = float(changed.median())
                difference = regime_median - baseline_median
                if difference > 0:
                    direction = "increase"
                elif difference < 0:
                    direction = "decrease"
                else:
                    direction = "unchanged"
                rows.append(
                    {
                        "fault_number": int(fault_number),
                        "simulation_run": int(simulation_run),
                        "regime": regime,
                        "property": property_name,
                        "baseline_objects": int(reference.notna().sum()),
                        "regime_objects": int(changed.notna().sum()),
                        "baseline_median": baseline_median,
                        "regime_median": regime_median,
                        "median_difference": difference,
                        "median_ratio": (
                            regime_median / baseline_median
                            if baseline_median != 0
                            else np.nan
                        ),
                        "direction": direction,
                        "cliffs_delta": cliffs_delta(reference, changed),
                    }
                )
    return pd.DataFrame(rows)


def summarize_reproducibility(
    characterization: pd.DataFrame,
    *,
    consistency_threshold: float = CONSISTENCY_THRESHOLD,
    cliffs_delta_threshold: float = CLIFFS_DELTA_THRESHOLD,
) -> pd.DataFrame:
    """Summarize direction and effect-size agreement across complete runs."""
    required = {
        "fault_number",
        "simulation_run",
        "regime",
        "property",
        "baseline_median",
        "regime_median",
        "median_difference",
        "direction",
        "cliffs_delta",
    }
    missing = required - set(characterization)
    if missing:
        raise ValueError(f"missing characterization columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    groups = characterization.groupby(
        ["fault_number", "regime", "property"], sort=True
    )
    for (fault_number, regime, property_name), group in groups:
        median_difference = float(group["median_difference"].median())
        if median_difference > 0:
            dominant_direction = "increase"
        elif median_difference < 0:
            dominant_direction = "decrease"
        else:
            dominant_direction = "unchanged"
        matching = int(group["direction"].eq(dominant_direction).sum())
        runs = int(group["simulation_run"].nunique())
        consistency = matching / runs if runs else np.nan
        median_cliffs_delta = float(group["cliffs_delta"].median())
        strength = abs(median_cliffs_delta) * consistency
        repeatable = bool(
            dominant_direction != "unchanged"
            and consistency >= consistency_threshold
            and abs(median_cliffs_delta) >= cliffs_delta_threshold
        )
        rows.append(
            {
                "fault_number": int(fault_number),
                "regime": regime,
                "property": property_name,
                "runs_evaluated": runs,
                "dominant_direction": dominant_direction,
                "direction_consistency": consistency,
                "median_baseline": float(group["baseline_median"].median()),
                "median_regime": float(group["regime_median"].median()),
                "median_difference": median_difference,
                "median_ratio": (
                    float(group["regime_median"].median())
                    / float(group["baseline_median"].median())
                    if float(group["baseline_median"].median()) != 0
                    else np.nan
                ),
                "median_cliffs_delta": median_cliffs_delta,
                "behavioral_strength": strength,
                "repeatable": repeatable,
            }
        )
    return pd.DataFrame(rows)


def build_signatures(
    reproducibility: pd.DataFrame,
    *,
    properties_per_regime: int = 3,
) -> pd.DataFrame:
    """Select the strongest reproducible changes for each fault and regime."""
    if properties_per_regime < 1:
        raise ValueError("properties_per_regime must be positive")
    ordered = reproducibility.sort_values(
        ["fault_number", "regime", "repeatable", "behavioral_strength"],
        ascending=[True, True, False, False],
    ).copy()
    signatures = ordered.groupby(
        ["fault_number", "regime"], sort=True
    ).head(properties_per_regime).copy()
    signatures["signature_rank"] = signatures.groupby(
        ["fault_number", "regime"], sort=False
    ).cumcount() + 1
    return signatures.reset_index(drop=True)


def summarize_coverage(objects: pd.DataFrame) -> pd.DataFrame:
    """Report object counts, including missing fault/run/regime combinations."""
    faults = sorted(objects["fault_number"].unique())
    runs = sorted(objects["simulation_run"].unique())
    regimes = ["pre_injection", *REGIMES]
    full_index = pd.MultiIndex.from_product(
        [faults, runs, regimes],
        names=["fault_number", "simulation_run", "regime"],
    )
    counts = (
        objects.groupby(["fault_number", "simulation_run", "regime"])
        .size()
        .reindex(full_index, fill_value=0)
        .rename("complete_object_count")
        .reset_index()
    )
    counts["has_complete_objects"] = counts["complete_object_count"].gt(0)
    return counts


def _records(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, object]]:
    clean = frame[columns].copy().replace({np.nan: None})
    return clean.to_dict(orient="records")


def run_query_catalog(
    objects: pd.DataFrame,
    reproducibility: pd.DataFrame,
    signatures: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, list[dict[str, object]]]]:
    """Execute ten deterministic behavioral questions."""
    early = objects.loc[objects["regime"].eq("early_response")]
    post = objects.loc[objects["regime"].eq("post_response")]

    query_functions: list[
        tuple[str, str, str, Callable[[], list[dict[str, object]]]]
    ] = [
        (
            "Q01",
            "What is the largest-amplitude oscillation for each fault?",
            "objects",
            lambda: _records(
                objects.loc[objects.groupby("fault_number")["amplitude"].idxmax()],
                ["fault_number", "simulation_run", "oscillation_id", "amplitude"],
            ),
        ),
        (
            "Q02",
            "What is the longest oscillation for each fault?",
            "objects",
            lambda: _records(
                objects.loc[objects.groupby("fault_number")["duration"].idxmax()],
                ["fault_number", "simulation_run", "oscillation_id", "duration"],
            ),
        ),
        (
            "Q03",
            "Which object first overlaps the early response in each run?",
            "objects",
            lambda: _records(
                early.loc[
                    early.groupby(["fault_number", "simulation_run"])[
                        "end_index"
                    ].idxmin()
                ],
                [
                    "fault_number",
                    "simulation_run",
                    "oscillation_id",
                    "start_index",
                    "end_index",
                ],
            ),
        ),
        (
            "Q04",
            "How many complete objects occur in each regime for each fault?",
            "objects",
            lambda: _records(
                objects.groupby(["fault_number", "regime"], as_index=False)
                .size()
                .rename(columns={"size": "object_count"}),
                ["fault_number", "regime", "object_count"],
            ),
        ),
        (
            "Q05",
            "Which fault has the greatest early-response amplitude increase?",
            "reproducibility",
            lambda: _records(
                reproducibility.loc[
                    reproducibility.loc[
                        reproducibility["regime"].eq("early_response")
                        & reproducibility["property"].eq("amplitude")
                    ]["median_difference"].idxmax()
                ].to_frame().T,
                ["fault_number", "median_difference", "direction_consistency"],
            ),
        ),
        (
            "Q06",
            "Which fault has the greatest sustained amplitude increase?",
            "reproducibility",
            lambda: _records(
                reproducibility.loc[
                    reproducibility.loc[
                        reproducibility["regime"].eq("post_response")
                        & reproducibility["property"].eq("amplitude")
                    ]["median_difference"].idxmax()
                ].to_frame().T,
                ["fault_number", "median_difference", "direction_consistency"],
            ),
        ),
        (
            "Q07",
            "Which faults show a repeatable increase in oscillation period?",
            "reproducibility",
            lambda: _records(
                reproducibility.loc[
                    reproducibility["property"].eq("period")
                    & reproducibility["repeatable"]
                    & reproducibility["dominant_direction"].eq("increase")
                ],
                [
                    "fault_number",
                    "regime",
                    "direction_consistency",
                    "median_cliffs_delta",
                ],
            ),
        ),
        (
            "Q08",
            "Which faults show a repeatable decrease in temporal symmetry?",
            "reproducibility",
            lambda: _records(
                reproducibility.loc[
                    reproducibility["property"].eq("temporal_symmetry")
                    & reproducibility["repeatable"]
                    & reproducibility["dominant_direction"].eq("decrease")
                ],
                [
                    "fault_number",
                    "regime",
                    "direction_consistency",
                    "median_cliffs_delta",
                ],
            ),
        ),
        (
            "Q09",
            "What is the strongest early-response signature for each fault?",
            "signatures",
            lambda: _records(
                signatures.loc[
                    signatures["regime"].eq("early_response")
                    & signatures["signature_rank"].eq(1)
                ],
                [
                    "fault_number",
                    "property",
                    "dominant_direction",
                    "behavioral_strength",
                    "repeatable",
                ],
            ),
        ),
        (
            "Q10",
            "What is the strongest sustained-response signature for each fault?",
            "signatures",
            lambda: _records(
                signatures.loc[
                    signatures["regime"].eq("post_response")
                    & signatures["signature_rank"].eq(1)
                ],
                [
                    "fault_number",
                    "property",
                    "dominant_direction",
                    "behavioral_strength",
                    "repeatable",
                ],
            ),
        ),
    ]

    source_sizes = {
        "objects": len(objects),
        "reproducibility": len(reproducibility),
        "signatures": len(signatures),
    }
    audit_rows = []
    results: dict[str, list[dict[str, object]]] = {}
    for query_id, question, source, function in query_functions:
        answer = function()
        results[query_id] = answer
        audit_rows.append(
            {
                "query_id": query_id,
                "question": question,
                "source_table": source,
                "source_rows": source_sizes[source],
                "result_rows": len(answer),
                "answered": True,
                "empty_result": not bool(answer),
            }
        )
    return pd.DataFrame(audit_rows), results


def run_audit(
    objects: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    characterization = characterize_regimes(objects)
    reproducibility = summarize_reproducibility(characterization)
    signatures = build_signatures(reproducibility)
    query_audit, query_results = run_query_catalog(
        objects, reproducibility, signatures
    )
    return (
        characterization,
        reproducibility,
        signatures,
        query_audit,
        query_results,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--objects",
        type=Path,
        default=Path("artifacts/tep/fault_comparison/objects.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/tep/behavioral_audit"),
    )
    args = parser.parse_args()

    objects = pd.read_csv(args.objects)
    coverage = summarize_coverage(objects)
    outputs = run_audit(objects)
    characterization, reproducibility, signatures, query_audit, query_results = (
        outputs
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    characterization.to_csv(
        args.output_dir / "regime_characterization.csv", index=False
    )
    coverage.to_csv(args.output_dir / "object_coverage.csv", index=False)
    reproducibility.to_csv(
        args.output_dir / "cross_run_reproducibility.csv", index=False
    )
    signatures.to_csv(args.output_dir / "behavioral_signatures.csv", index=False)
    query_audit.to_csv(args.output_dir / "query_audit.csv", index=False)
    (args.output_dir / "query_results.json").write_text(
        json.dumps(query_results, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "input_objects": str(args.objects),
        "faults": sorted(objects["fault_number"].unique().astype(int).tolist()),
        "runs": sorted(objects["simulation_run"].unique().astype(int).tolist()),
        "baseline_regime": "pre_injection",
        "comparison_regimes": list(REGIMES),
        "properties": list(FEATUREGRAPH_FEATURES),
        "effect_size": "Cliff's delta; positive means regime values exceed baseline",
        "repeatability_rule": {
            "minimum_direction_consistency": CONSISTENCY_THRESHOLD,
            "minimum_absolute_median_cliffs_delta": CLIFFS_DELTA_THRESHOLD,
        },
        "query_count": len(query_audit),
        "notes": [
            "No predictive model is fit by this audit.",
            "Every regime comparison uses the pre-injection objects from the same run.",
            "Only complete reactor-pressure oscillation objects are audited.",
            (
                "Object coverage records zero-object fault/run/regime "
                "combinations."
            ),
        ],
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    strongest = signatures.loc[signatures["signature_rank"].eq(1), [
        "fault_number",
        "regime",
        "property",
        "dominant_direction",
        "direction_consistency",
        "median_cliffs_delta",
        "repeatable",
    ]]
    print(strongest.to_string(index=False))
    answered = int(query_audit["answered"].sum())
    print("\nQueries answered:", answered, "/", len(query_audit))
    print("Artifacts written to", args.output_dir)


if __name__ == "__main__":
    main()
