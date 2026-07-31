import pandas as pd
import pytest

from experiments.rl.analyze import analyze


def test_analysis_computes_paired_auc_difference() -> None:
    rows = []
    for seed in [0, 1]:
        for step, raw, augmented in [(0, 0.0, 0.0), (10, 1.0, 3.0)]:
            rows.extend(
                [
                    {
                        "environment": "cartpole",
                        "representation": "raw",
                        "seed": seed,
                        "step": step,
                        "mean_return": raw,
                    },
                    {
                        "environment": "cartpole",
                        "representation": "augmented",
                        "seed": seed,
                        "step": step,
                        "mean_return": augmented,
                    },
                ]
            )

    result = analyze(pd.DataFrame(rows), bootstrap_samples=100, seed=1)
    comparison = result["comparisons"][0]

    assert comparison["representation"] == "augmented"
    assert comparison["paired_seeds"] == [0, 1]
    assert comparison["mean_auc_difference"] == 1.0
    assert comparison["bootstrap_95_low"] == 1.0
    assert comparison["bootstrap_95_high"] == 1.0


def test_analysis_requires_complete_curves() -> None:
    incomplete = pd.DataFrame(
        {
            "environment": ["cartpole"],
            "representation": ["raw"],
            "seed": [0],
            "step": [0],
            "mean_return": [1.0],
        }
    )

    with pytest.raises(ValueError):
        analyze(incomplete)
