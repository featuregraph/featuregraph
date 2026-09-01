"""Evaluate Nori downstream of explicit PhysioNet protocol objects.

The source representation is produced without modification by
``run_physionet_wearable_protocol_study.py``. This runner asks a separate,
predictive question: can physiological measurements attached to those objects
estimate the source self-report for participants withheld from model context?

This is a small interoperability demonstration, not a stress detector or a
reproduction of Synthefy's published benchmark suite.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from featuregraph.studies import (
    git_commit_or_none,
    package_versions,
    write_frames,
    write_json,
)

try:
    from scripts.run_physionet_wearable_protocol_study import (
        download_sources,
        run_study,
    )
except ModuleNotFoundError:
    from run_physionet_wearable_protocol_study import download_sources, run_study

RANDOM_SEED = 20260827
N_SPLITS = 5
TARGET_COLUMN = "self_reported_stress"
GROUP_COLUMN = "subject_id"
MODEL_ORDER = ("train_mean", "nori_6m", "xgboost", "lightgbm")
CONDITION_ORDER = ("physiology_only", "physiology_plus_protocol")
PHYSIOLOGY_COLUMNS = tuple(
    f"{signal}_{measure}"
    for signal in ("hr", "eda", "temp")
    for measure in ("mean", "median", "min", "max")
)
PROTOCOL_STATES = (
    "baseline",
    "stroop",
    "first_rest",
    "tmct",
    "second_rest",
    "real_opinion",
    "opposite_opinion",
    "subtract",
)
MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "train_mean": {"strategy": "mean"},
    "nori_6m": {
        "model": "nori-6m",
        "device": "cpu",
        "augmentations": ["yj"],
        "strict_pipeline": True,
    },
    "xgboost": {
        "n_estimators": 300,
        "max_depth": 3,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_lambda": 1.0,
        "random_state": RANDOM_SEED,
        "n_jobs": 1,
    },
    "lightgbm": {
        "n_estimators": 300,
        "learning_rate": 0.03,
        "num_leaves": 15,
        "min_child_samples": 10,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": RANDOM_SEED,
        "n_jobs": 1,
        "verbosity": -1,
    },
}
STUDY_CONTRACT = {
    "version": "physionet-nori-demonstration-v1",
    "question": (
        "Can models estimate source self-reported stress from physiological "
        "measurements attached to explicit protocol occurrences for participants "
        "withheld from model context?"
    ),
    "source_representation": "physionet-wearable-protocol-study-v1",
    "target": TARGET_COLUMN,
    "group": GROUP_COLUMN,
    "split": {
        "type": "participant-held-out stratified cross-validation",
        "folds": N_SPLITS,
        "strata": "protocol cohort crossed with low/high participant mean target",
        "random_seed": RANDOM_SEED,
    },
    "conditions": {
        "physiology_only": list(PHYSIOLOGY_COLUMNS),
        "physiology_plus_protocol": [
            *PHYSIOLOGY_COLUMNS,
            "one-hot declared protocol state",
        ],
    },
    "excluded_predictors": [
        "subject identifier",
        "cohort identifier",
        "timestamps",
        "object identifier",
        "source self-report",
    ],
    "models": MODEL_CONFIGS,
    "primary_metric": "participant-held-out mean absolute error",
    "secondary_metrics": ["root mean squared error", "R squared"],
    "interpretation_boundary": (
        "The demonstration evaluates downstream regression from preserved protocol "
        "objects. It does not validate a stress biomarker, establish causality, or "
        "reproduce Synthefy's benchmark claims."
    ),
}


def feature_matrix(objects: pd.DataFrame, condition: str) -> pd.DataFrame:
    """Build the frozen numeric design matrix for one declared condition."""
    if condition not in CONDITION_ORDER:
        raise ValueError(f"Unknown condition: {condition}")
    required = {*PHYSIOLOGY_COLUMNS, "protocol_state"}
    missing = required.difference(objects.columns)
    if missing:
        raise ValueError(f"Missing source columns: {sorted(missing)}")

    features = objects.loc[:, PHYSIOLOGY_COLUMNS].astype(float).copy()
    if condition == "physiology_plus_protocol":
        declared = pd.Categorical(
            objects["protocol_state"], categories=PROTOCOL_STATES
        )
        protocol = pd.get_dummies(
            declared, prefix="protocol", dtype=float
        ).set_axis(objects.index)
        features = pd.concat([features, protocol], axis=1)

    values = features.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"{condition} contains missing or non-finite predictors")
    if GROUP_COLUMN in features or TARGET_COLUMN in features:
        raise AssertionError("Group or target leaked into the design matrix")
    return features


def make_fold_assignments(objects: pd.DataFrame) -> pd.DataFrame:
    """Create deterministic participant-held-out folds balanced by declared strata."""
    from sklearn.model_selection import StratifiedKFold

    subjects = (
        objects.groupby([GROUP_COLUMN, "cohort"], as_index=False)
        .agg(
            participant_mean_target=(TARGET_COLUMN, "mean"),
            participant_rows=(TARGET_COLUMN, "size"),
        )
        .sort_values(GROUP_COLUMN)
        .reset_index(drop=True)
    )
    subjects["target_stratum"] = pd.qcut(
        subjects["participant_mean_target"],
        q=2,
        labels=("low", "high"),
    ).astype(str)
    subjects["stratum"] = subjects["cohort"] + "_" + subjects["target_stratum"]
    splitter = StratifiedKFold(
        n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_SEED
    )
    subjects["fold"] = 0
    for fold, (_, test_index) in enumerate(
        splitter.split(subjects, subjects["stratum"]), start=1
    ):
        subjects.loc[test_index, "fold"] = fold
    validate_fold_assignments(objects, subjects)
    return subjects


def validate_fold_assignments(
    objects: pd.DataFrame, assignments: pd.DataFrame
) -> None:
    """Reject split tables that leak or omit participants."""
    expected_subjects = set(objects[GROUP_COLUMN].unique())
    assigned_subjects = set(assignments[GROUP_COLUMN])
    if expected_subjects != assigned_subjects:
        raise AssertionError("Fold assignment does not contain every participant once")
    if assignments[GROUP_COLUMN].duplicated().any():
        raise AssertionError("A participant appears in more than one fold")
    if set(assignments["fold"]) != set(range(1, N_SPLITS + 1)):
        raise AssertionError("Fold labels are incomplete")
    cohort_counts = assignments.groupby("fold")["cohort"].nunique()
    if not cohort_counts.eq(2).all():
        raise AssertionError("Every fold must contain both protocol cohorts")


def model_registry() -> dict[str, Any]:
    """Instantiate the four frozen model configurations."""
    from lightgbm import LGBMRegressor
    from sklearn.dummy import DummyRegressor
    from synthefy_nori import NoriRegressor
    from xgboost import XGBRegressor

    return {
        "train_mean": DummyRegressor(**MODEL_CONFIGS["train_mean"]),
        "nori_6m": NoriRegressor(
            model=MODEL_CONFIGS["nori_6m"]["model"],
            device=MODEL_CONFIGS["nori_6m"]["device"],
            augmentations=tuple(MODEL_CONFIGS["nori_6m"]["augmentations"]),
        ),
        "xgboost": XGBRegressor(**MODEL_CONFIGS["xgboost"]),
        "lightgbm": LGBMRegressor(**MODEL_CONFIGS["lightgbm"]),
    }


def fit_predict(
    model_name: str,
    model: Any,
    x_train: Any,
    y_train: Any,
    x_test: Any,
) -> np.ndarray:
    """Fit/store context and predict, rejecting any Nori pipeline degradation."""
    model.fit(x_train, y_train)
    if model_name == "nori_6m":
        from synthefy_nori import strict_pipeline

        with strict_pipeline():
            prediction = model.predict(x_test)
    else:
        prediction = model.predict(x_test)
    result = np.asarray(prediction, dtype=float).reshape(-1)
    if not np.isfinite(result).all():
        raise AssertionError(f"{model_name} produced non-finite predictions")
    return result


def regression_metrics(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    """Compute the frozen regression metrics without hidden model state."""
    residual = actual.to_numpy(dtype=float) - predicted.to_numpy(dtype=float)
    centered = actual.to_numpy(dtype=float) - float(actual.mean())
    denominator = float(np.square(centered).sum())
    return {
        "mae": float(np.abs(residual).mean()),
        "rmse": float(np.sqrt(np.square(residual).mean())),
        "r2": float(1.0 - np.square(residual).sum() / denominator),
    }


def evaluate(objects: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Run all conditions and models on identical participant-held-out folds."""
    assignments = make_fold_assignments(objects)
    fold_by_subject = assignments.set_index(GROUP_COLUMN)["fold"]
    prediction_parts = []
    fold_metric_rows = []

    for condition in CONDITION_ORDER:
        features = feature_matrix(objects, condition)
        models = model_registry()
        for model_name in MODEL_ORDER:
            model = models[model_name]
            for fold in range(1, N_SPLITS + 1):
                test_mask = objects[GROUP_COLUMN].map(fold_by_subject).eq(fold)
                train_mask = ~test_mask
                train_subjects = set(objects.loc[train_mask, GROUP_COLUMN])
                test_subjects = set(objects.loc[test_mask, GROUP_COLUMN])
                if train_subjects.intersection(test_subjects):
                    raise AssertionError("Participant leakage detected")

                predicted = fit_predict(
                    model_name,
                    model,
                    features.loc[train_mask],
                    objects.loc[train_mask, TARGET_COLUMN],
                    features.loc[test_mask],
                )
                fold_predictions = objects.loc[
                    test_mask,
                    [GROUP_COLUMN, "cohort", "protocol_state", TARGET_COLUMN],
                ].copy()
                fold_predictions["fold"] = fold
                fold_predictions["condition"] = condition
                fold_predictions["model"] = model_name
                fold_predictions["prediction"] = predicted
                prediction_parts.append(fold_predictions)

                metrics = regression_metrics(
                    fold_predictions[TARGET_COLUMN], fold_predictions["prediction"]
                )
                fold_metric_rows.append(
                    {
                        "condition": condition,
                        "model": model_name,
                        "fold": fold,
                        "test_participants": len(test_subjects),
                        "test_rows": len(fold_predictions),
                        **metrics,
                    }
                )

    predictions = pd.concat(prediction_parts, ignore_index=True)
    fold_metrics = pd.DataFrame(fold_metric_rows)
    summary_rows = []
    subject_metric_rows = []
    for (condition, model_name), frame in predictions.groupby(
        ["condition", "model"], sort=False
    ):
        summary_rows.append(
            {
                "condition": condition,
                "model": model_name,
                "participants": frame[GROUP_COLUMN].nunique(),
                "rows": len(frame),
                **regression_metrics(frame[TARGET_COLUMN], frame["prediction"]),
            }
        )
        for subject_id, subject in frame.groupby(GROUP_COLUMN):
            subject_metric_rows.append(
                {
                    "condition": condition,
                    "model": model_name,
                    GROUP_COLUMN: subject_id,
                    "fold": int(subject["fold"].iloc[0]),
                    "rows": len(subject),
                    **regression_metrics(
                        subject[TARGET_COLUMN], subject["prediction"]
                    ),
                }
            )
    summary = pd.DataFrame(summary_rows)
    summary["mae_rank_within_condition"] = summary.groupby("condition")["mae"].rank(
        method="min"
    ).astype(int)
    subject_metrics = pd.DataFrame(subject_metric_rows)
    paired_rows = []
    for condition in CONDITION_ORDER:
        nori = subject_metrics[
            (subject_metrics["condition"] == condition)
            & (subject_metrics["model"] == "nori_6m")
        ].set_index(GROUP_COLUMN)["mae"]
        for comparison in ("train_mean", "xgboost", "lightgbm"):
            other = subject_metrics[
                (subject_metrics["condition"] == condition)
                & (subject_metrics["model"] == comparison)
            ].set_index(GROUP_COLUMN)["mae"]
            difference = nori - other
            paired_rows.append(
                {
                    "condition": condition,
                    "comparison": comparison,
                    "participants": len(difference),
                    "median_nori_minus_comparison_mae": float(difference.median()),
                    "nori_lower_mae_participants": int(difference.lt(0).sum()),
                    "comparison_lower_mae_participants": int(difference.gt(0).sum()),
                    "ties": int(difference.eq(0).sum()),
                }
            )
    paired_comparisons = pd.DataFrame(paired_rows)
    validate_predictions(objects, predictions)
    return {
        "fold_assignments": assignments,
        "predictions": predictions,
        "fold_metrics": fold_metrics,
        "summary": summary,
        "subject_metrics": subject_metrics,
        "paired_comparisons": paired_comparisons,
    }


def validate_predictions(objects: pd.DataFrame, predictions: pd.DataFrame) -> None:
    """Check coverage, finiteness, and identical fold membership."""
    expected = len(objects) * len(CONDITION_ORDER) * len(MODEL_ORDER)
    if len(predictions) != expected:
        raise AssertionError(
            f"Expected {expected} predictions; found {len(predictions)}"
        )
    if not np.isfinite(predictions["prediction"]).all():
        raise AssertionError("Non-finite prediction found")
    counts = predictions.groupby(["condition", "model"]).size()
    if not counts.eq(len(objects)).all():
        raise AssertionError("A model-condition pair lacks complete row coverage")
    membership = predictions.groupby(
        ["condition", "model", GROUP_COLUMN]
    )["fold"].nunique()
    if not membership.eq(1).all():
        raise AssertionError("A participant crossed fold boundaries")


DEMONSTRATION_PACKAGES = (
    "featuregraph",
    "lightgbm",
    "numpy",
    "pandas",
    "scikit-learn",
    "synthefy-nori",
    "torch",
    "xgboost-cpu",
)


def write_outputs(results: dict[str, pd.DataFrame], output: Path) -> None:
    write_frames(results, output, compression=None)
    provenance = {
        "contract": STUDY_CONTRACT,
        "dataset": {
            "name": (
                "Wearable Device Dataset from Induced Stress and Structured "
                "Exercise Sessions"
            ),
            "version": "1.0.1",
            "doi": "10.13026/he0v-tf17",
        },
        "package_versions": package_versions(*DEMONSTRATION_PACKAGES),
        "featuregraph_source_revision_before_result_commit": git_commit_or_none(),
    }
    write_json(output / "study_contract.json", provenance)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path("data/physionet_wearable"))
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/physionet_nori_demonstration")
    )
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    np.random.seed(RANDOM_SEED)
    try:
        import torch

        torch.manual_seed(RANDOM_SEED)
        torch.use_deterministic_algorithms(True)
    except ImportError:
        pass

    download_sources(args.cache, workers=args.workers)
    source = run_study(args.cache)
    objects = source["study_objects"]
    results = evaluate(objects)
    write_outputs(results, args.output)
    print(results["summary"].to_string(index=False))
    print("\nNori paired participant comparisons")
    print(results["paired_comparisons"].to_string(index=False))


if __name__ == "__main__":
    main()
