"""Compare raw and FeatureGraph representations across TEP faults.

The experiment fits one classifier per fault, target, and representation. Complete
simulation runs are held out, and one fault-free run is retained as an external
negative control.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import featuregraph as fg
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from featuregraph.utils._eastman import GITHUB_REVISION

DEFAULT_FAULTS = (1, 2, 4, 6, 7, 12, 14)
DEFAULT_TRAIN_RUNS = (1, 2, 3)
DEFAULT_TEST_RUNS = (4, 5)
DEFAULT_FAULT_START = 600
DEFAULT_RESPONSE_END = 1200

RAW_FEATURES = (
    "raw_mean",
    "raw_std",
    "raw_min",
    "raw_max",
    "raw_range",
    "raw_start",
    "raw_end",
    "raw_delta",
    "raw_abs_delta",
)
FEATUREGRAPH_FEATURES = (
    "rise_duration",
    "fall_duration",
    "duration",
    "period",
    "amplitude",
    "rising_mean_rate",
    "falling_mean_rate",
    "peak_rise_rate",
    "peak_fall_rate",
    "temporal_symmetry",
)
REPRESENTATIONS = {
    "raw_context": RAW_FEATURES,
    "featuregraph": FEATUREGRAPH_FEATURES,
    "combined": RAW_FEATURES + FEATUREGRAPH_FEATURES,
}
TARGETS = ("post_injection", "early_response")


def construct_examples(
    observations: pd.DataFrame,
    *,
    signal: str = "reactor_pressure",
    fault_start: int = DEFAULT_FAULT_START,
    response_end: int = DEFAULT_RESPONSE_END,
    smooth_window: int = 20,
    diff_lag: int = 10,
) -> pd.DataFrame:
    """Construct complete oscillation objects and matched raw summaries."""
    required = {"fault_number", "simulation_run", signal}
    missing = required - set(observations)
    if missing:
        raise ValueError(f"missing observation columns: {sorted(missing)}")
    if response_end <= fault_start:
        raise ValueError("response_end must be greater than fault_start")

    observations = observations.reset_index(drop=True)
    constructor = fg.oscillation.Oscillation(
        signals=signal,
        group=["fault_number", "simulation_run"],
        smooth_signal=True,
        smooth_window=smooth_window,
        diff_lag=diff_lag,
    )
    features = constructor.fit_transform(observations)
    objects = constructor.summarize(features, signal=signal).table.copy()
    objects = objects.loc[objects["is_complete"]].reset_index(drop=True)

    raw_rows = []
    for row in objects.itertuples(index=False):
        start = int(row.start_index)
        end = int(row.end_index)
        segment = observations[signal].iloc[start : end + 1]
        raw_rows.append(
            {
                "raw_mean": segment.mean(),
                "raw_std": segment.std(ddof=0),
                "raw_min": segment.min(),
                "raw_max": segment.max(),
                "raw_range": segment.max() - segment.min(),
                "raw_start": segment.iloc[0],
                "raw_end": segment.iloc[-1],
                "raw_delta": segment.iloc[-1] - segment.iloc[0],
                "raw_abs_delta": abs(segment.iloc[-1] - segment.iloc[0]),
            }
        )

    examples = pd.concat([objects, pd.DataFrame(raw_rows)], axis=1)
    fault_number = int(examples["fault_number"].iloc[0])
    if fault_number == 0:
        examples["post_injection"] = 0
        examples["early_response"] = 0
        examples["regime"] = "fault_free"
        return examples

    examples["post_injection"] = (
        examples["end_index"] >= fault_start
    ).astype(int)
    examples["early_response"] = (
        (examples["end_index"] >= fault_start)
        & (examples["start_index"] <= response_end)
    ).astype(int)
    examples["regime"] = np.select(
        [
            examples["end_index"] < fault_start,
            examples["start_index"] <= response_end,
        ],
        ["pre_injection", "early_response"],
        default="post_response",
    )
    return examples


def load_fault_examples(
    fault_number: int,
    runs: Iterable[int],
    *,
    signal: str,
    fault_start: int,
    response_end: int,
    smooth_window: int,
    diff_lag: int,
) -> pd.DataFrame:
    """Load selected runs and construct one object table for a fault."""
    frames = []
    for run in runs:
        print(f"Constructing Fault {fault_number}, run {run}...")
        observations = fg.datasets.eastman(
            dataset="faulty_training",
            fault_number=fault_number,
            simulation_run=run,
        )
        frames.append(
            construct_examples(
                observations,
                signal=signal,
                fault_start=fault_start,
                response_end=response_end,
                smooth_window=smooth_window,
                diff_lag=diff_lag,
            )
        )
    return pd.concat(frames, ignore_index=True)


def evaluate_fault(
    fault_examples: pd.DataFrame,
    control_examples: pd.DataFrame,
    *,
    fault_number: int,
    train_runs: Iterable[int] = DEFAULT_TRAIN_RUNS,
    test_runs: Iterable[int] = DEFAULT_TEST_RUNS,
    fault_start: int = DEFAULT_FAULT_START,
    random_state: int = 1729,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate representations with complete held-out simulation runs."""
    train_runs = tuple(train_runs)
    test_runs = tuple(test_runs)
    overlap = set(train_runs) & set(test_runs)
    if overlap:
        raise ValueError(f"train and test runs overlap: {sorted(overlap)}")

    train = fault_examples[
        fault_examples["simulation_run"].isin(train_runs)
    ].copy()
    test = fault_examples[
        fault_examples["simulation_run"].isin(test_runs)
    ].copy()
    if train.empty or test.empty:
        raise ValueError("both training and testing examples are required")

    evaluation_rows = []
    prediction_frames = []
    for target in TARGETS:
        y_train = train[target].astype(int)
        y_test = test[target].astype(int)
        if y_train.nunique() != 2 or y_test.nunique() != 2:
            raise ValueError(
                f"target {target!r} requires both classes in train and test"
            )

        for representation, feature_names in REPRESENTATIONS.items():
            model = make_pipeline(
                SimpleImputer(strategy="median"),
                StandardScaler(),
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=random_state,
                ),
            )
            model.fit(train[list(feature_names)], y_train)

            probability = model.predict_proba(test[list(feature_names)])[:, 1]
            prediction = (probability >= 0.5).astype(int)
            control_probability = model.predict_proba(
                control_examples[list(feature_names)]
            )[:, 1]
            control_prediction = (control_probability >= 0.5).astype(int)

            tn, fp, fn, tp = confusion_matrix(
                y_test, prediction, labels=[0, 1]
            ).ravel()
            delays = []
            for run in test_runs:
                run_rows = test[
                    test["simulation_run"].eq(run)
                ].copy()
                run_rows["prediction"] = prediction[
                    test["simulation_run"].eq(run).to_numpy()
                ]
                detections = run_rows[
                    (run_rows["end_index"] >= fault_start)
                    & run_rows["prediction"].eq(1)
                ]
                if not detections.empty:
                    delays.append(
                        max(
                            0.0,
                            float(detections["end_index"].min() - fault_start),
                        )
                    )

            evaluation_rows.append(
                {
                    "fault_number": fault_number,
                    "target": target,
                    "representation": representation,
                    "feature_count": len(feature_names),
                    "train_objects": len(train),
                    "test_objects": len(test),
                    "positive_test_objects": int(y_test.sum()),
                    "roc_auc": roc_auc_score(y_test, probability),
                    "average_precision": average_precision_score(
                        y_test, probability
                    ),
                    "balanced_accuracy": balanced_accuracy_score(
                        y_test, prediction
                    ),
                    "sensitivity": tp / (tp + fn),
                    "specificity": tn / (tn + fp),
                    "faultfree_false_positive_rate": control_prediction.mean(),
                    "median_detection_delay_samples": (
                        float(np.median(delays)) if delays else np.nan
                    ),
                }
            )

            prediction_frame = test[
                [
                    "fault_number",
                    "simulation_run",
                    "oscillation_id",
                    "start_index",
                    "peak_index",
                    "end_index",
                    "regime",
                ]
            ].copy()
            prediction_frame["target"] = target
            prediction_frame["representation"] = representation
            prediction_frame["label"] = y_test.to_numpy()
            prediction_frame["probability"] = probability
            prediction_frame["prediction"] = prediction
            prediction_frames.append(prediction_frame)

    return (
        pd.DataFrame(evaluation_rows),
        pd.concat(prediction_frames, ignore_index=True),
    )


def run_comparison(
    *,
    faults: Iterable[int] = DEFAULT_FAULTS,
    signal: str = "reactor_pressure",
    train_runs: Iterable[int] = DEFAULT_TRAIN_RUNS,
    test_runs: Iterable[int] = DEFAULT_TEST_RUNS,
    fault_start: int = DEFAULT_FAULT_START,
    response_end: int = DEFAULT_RESPONSE_END,
    smooth_window: int = 20,
    diff_lag: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run independent representation comparisons for selected faults."""
    faults = tuple(dict.fromkeys(int(fault) for fault in faults))
    train_runs = tuple(train_runs)
    test_runs = tuple(test_runs)
    if not faults:
        raise ValueError("at least one fault is required")

    print("Constructing fault-free control...")
    control_observations = fg.datasets.eastman(
        dataset="faultfree_training",
        fault_number=0,
        simulation_run=1,
    )
    control_examples = construct_examples(
        control_observations,
        signal=signal,
        fault_start=fault_start,
        response_end=response_end,
        smooth_window=smooth_window,
        diff_lag=diff_lag,
    )

    all_objects = []
    all_evaluations = []
    all_predictions = []
    runs = (*train_runs, *test_runs)
    for fault_number in faults:
        fault_examples = load_fault_examples(
            fault_number,
            runs,
            signal=signal,
            fault_start=fault_start,
            response_end=response_end,
            smooth_window=smooth_window,
            diff_lag=diff_lag,
        )
        evaluation, predictions = evaluate_fault(
            fault_examples,
            control_examples,
            fault_number=fault_number,
            train_runs=train_runs,
            test_runs=test_runs,
            fault_start=fault_start,
        )
        all_objects.append(fault_examples)
        all_evaluations.append(evaluation)
        all_predictions.append(predictions)

    return (
        pd.concat(all_evaluations, ignore_index=True),
        pd.concat(all_predictions, ignore_index=True),
        pd.concat(all_objects, ignore_index=True),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--faults", nargs="+", type=int, default=list(DEFAULT_FAULTS)
    )
    parser.add_argument("--signal", default="reactor_pressure")
    parser.add_argument(
        "--train-runs", nargs="+", type=int, default=list(DEFAULT_TRAIN_RUNS)
    )
    parser.add_argument(
        "--test-runs", nargs="+", type=int, default=list(DEFAULT_TEST_RUNS)
    )
    parser.add_argument("--fault-start", type=int, default=DEFAULT_FAULT_START)
    parser.add_argument("--response-end", type=int, default=DEFAULT_RESPONSE_END)
    parser.add_argument("--smooth-window", type=int, default=20)
    parser.add_argument("--diff-lag", type=int, default=10)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/tep/fault_comparison"),
    )
    args = parser.parse_args()

    evaluation, predictions, objects = run_comparison(
        faults=args.faults,
        signal=args.signal,
        train_runs=args.train_runs,
        test_runs=args.test_runs,
        fault_start=args.fault_start,
        response_end=args.response_end,
        smooth_window=args.smooth_window,
        diff_lag=args.diff_lag,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    evaluation.to_csv(args.output_dir / "evaluation.csv", index=False)
    predictions.to_csv(
        args.output_dir / "heldout_predictions.csv", index=False
    )
    objects.to_csv(args.output_dir / "objects.csv", index=False)

    manifest = {
        "source_revision": GITHUB_REVISION,
        "faults": args.faults,
        "signal": args.signal,
        "fault_start_index": args.fault_start,
        "early_response_end_index": args.response_end,
        "train_runs": args.train_runs,
        "test_runs": args.test_runs,
        "smooth_window": args.smooth_window,
        "diff_lag": args.diff_lag,
        "representations": {
            name: list(features)
            for name, features in REPRESENTATIONS.items()
        },
        "notes": [
            "One classifier is fit independently for each fault.",
            "Raw-context features use FeatureGraph object boundaries.",
            "The early-response horizon is fixed across faults for comparison.",
            "The fault-free trajectory is an external negative control.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    columns = [
        "fault_number",
        "target",
        "representation",
        "roc_auc",
        "average_precision",
        "balanced_accuracy",
        "faultfree_false_positive_rate",
        "median_detection_delay_samples",
    ]
    print(evaluation[columns].to_string(index=False))
    print("\nArtifacts written to", args.output_dir)


if __name__ == "__main__":
    main()
