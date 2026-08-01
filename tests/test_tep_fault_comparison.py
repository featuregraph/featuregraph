import pandas as pd
import pytest

from experiments.tep.compare_faults import (
    FEATUREGRAPH_FEATURES,
    RAW_FEATURES,
    construct_examples,
    evaluate_fault,
)


def _examples() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for run in range(1, 6):
        for object_id, (start, end) in enumerate(
            [(500, 590), (590, 650), (650, 900), (1250, 1400)],
            start=1,
        ):
            row = {
                "fault_number": 1,
                "simulation_run": run,
                "oscillation_id": object_id,
                "start_index": start,
                "peak_index": (start + end) / 2,
                "end_index": end,
                "regime": (
                    "pre_injection"
                    if end < 600
                    else "early_response"
                    if start <= 1200
                    else "post_response"
                ),
                "post_injection": int(end >= 600),
                "early_response": int(end >= 600 and start <= 1200),
            }
            for index, name in enumerate(RAW_FEATURES):
                row[name] = float(index + row["post_injection"])
            for index, name in enumerate(FEATUREGRAPH_FEATURES):
                row[name] = float(index + row["early_response"])
            rows.append(row)

    control = pd.DataFrame(rows[:4]).copy()
    control["fault_number"] = 0
    control["simulation_run"] = 1
    control["post_injection"] = 0
    control["early_response"] = 0
    control["regime"] = "fault_free"
    return pd.DataFrame(rows), control


def test_evaluate_fault_returns_each_target_and_representation() -> None:
    examples, control = _examples()

    evaluation, predictions = evaluate_fault(
        examples,
        control,
        fault_number=1,
    )

    assert len(evaluation) == 6
    assert set(evaluation["target"]) == {
        "post_injection",
        "early_response",
    }
    assert set(evaluation["representation"]) == {
        "raw_context",
        "featuregraph",
        "combined",
    }
    assert set(predictions["simulation_run"]) == {4, 5}


def test_evaluate_fault_rejects_run_leakage() -> None:
    examples, control = _examples()

    with pytest.raises(ValueError, match="overlap"):
        evaluate_fault(
            examples,
            control,
            fault_number=1,
            train_runs=(1, 2, 3),
            test_runs=(3, 4),
        )


def test_construct_examples_requires_signal_and_group_columns() -> None:
    with pytest.raises(ValueError, match="missing observation columns"):
        construct_examples(pd.DataFrame({"reactor_pressure": [1.0]}))
