"""Paired-seed analysis for FeatureGraph RL learning curves."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def analyze(
    curves: pd.DataFrame,
    *,
    baseline: str = "raw",
    bootstrap_samples: int = 10_000,
    seed: int = 1729,
) -> dict[str, object]:
    """Compare normalized learning-curve area with paired bootstrap intervals."""
    required = {"environment", "representation", "seed", "step", "mean_return"}
    missing = required - set(curves)
    if missing:
        raise ValueError(f"missing curve columns: {sorted(missing)}")
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")

    areas = (
        curves.sort_values("step")
        .groupby(["environment", "representation", "seed"], sort=False)
        .apply(_normalized_area, include_groups=False)
        .rename("normalized_auc")
        .reset_index()
    )
    results: list[dict[str, object]] = []
    rng = np.random.default_rng(seed)
    for environment in areas["environment"].unique():
        environment_areas = areas[areas["environment"] == environment]
        baseline_areas = environment_areas[
            environment_areas["representation"] == baseline
        ][["seed", "normalized_auc"]].rename(
            columns={"normalized_auc": "baseline_auc"}
        )
        for representation in environment_areas["representation"].unique():
            if representation == baseline:
                continue
            candidate = environment_areas[
                environment_areas["representation"] == representation
            ][["seed", "normalized_auc"]]
            paired = baseline_areas.merge(candidate, on="seed", validate="one_to_one")
            if paired.empty:
                continue
            differences = (
                paired["normalized_auc"] - paired["baseline_auc"]
            ).to_numpy()
            bootstrap = rng.choice(
                differences,
                size=(bootstrap_samples, len(differences)),
                replace=True,
            ).mean(axis=1)
            results.append(
                {
                    "environment": environment,
                    "baseline": baseline,
                    "representation": representation,
                    "paired_seeds": paired["seed"].astype(int).tolist(),
                    "mean_auc_difference": float(differences.mean()),
                    "median_auc_difference": float(np.median(differences)),
                    "bootstrap_95_low": float(np.quantile(bootstrap, 0.025)),
                    "bootstrap_95_high": float(np.quantile(bootstrap, 0.975)),
                }
            )
    return {"metric": "normalized_learning_curve_auc", "comparisons": results}


def _normalized_area(group: pd.DataFrame) -> float:
    steps = group["step"].to_numpy(dtype=float)
    returns = group["mean_return"].to_numpy(dtype=float)
    if len(steps) < 2 or steps[-1] <= steps[0]:
        raise ValueError("each learning curve requires at least two distinct steps")
    return float(np.trapezoid(returns, steps) / (steps[-1] - steps[0]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("curves", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()
    result = analyze(
        pd.read_csv(args.curves),
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
