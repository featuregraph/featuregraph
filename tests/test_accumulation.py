import pandas as pd
import pytest

from featuregraph.behaviors.accumulation import Accumulation
from featuregraph.behaviors.oscillation import Oscillation


def oscillation_features(df: pd.DataFrame) -> pd.DataFrame:
    return Oscillation("signal", diff_lag=1).fit_transform(df)


def test_accumulation_requires_parent_wave_ids() -> None:
    behavior = Accumulation("signal")

    with pytest.raises(ValueError, match="requires existing wave IDs"):
        behavior.fit_transform(pd.DataFrame({"signal": [1.0]}))


def test_accumulation_constructs_contribution_and_running_total(
    triangular_signal: pd.DataFrame,
) -> None:
    features = oscillation_features(triangular_signal)
    behavior = Accumulation("signal", threshold="min")

    result = behavior.fit_transform(features)

    wave = result.loc[result["signal_wave_id"].eq(1)]
    assert wave["signal_accumulation_threshold"].tolist() == [0.0] * 4
    assert wave["signal_accumulation_contribution"].tolist() == [1.0, 2.0, 1.0, 0.0]
    assert wave["signal_accumulation"].tolist() == [1.0, 3.0, 4.0, 4.0]
    assert wave["signal_accumulation_id"].tolist() == [1] * 4
    assert result.loc[2, "signal_peak"]
    assert result.loc[2, "signal_accumulation"] == 3


def test_accumulation_summary_has_expected_intrinsic_properties(
    triangular_signal: pd.DataFrame,
) -> None:
    features = oscillation_features(triangular_signal)
    behavior = Accumulation("signal", threshold="min")
    result = behavior.fit_transform(features)

    objects = behavior.summarize(result, "signal")
    summary = objects.table
    wave = summary.loc[summary["accumulation_id"].eq(1)].iloc[0]

    assert objects.behavior_type == "accumulation"
    assert objects.parent_behavior == "oscillation"
    assert objects.features is result
    assert wave["start_index"] == 1
    assert wave["end_index"] == 4
    assert wave["duration"] == 4
    assert wave["baseline"] == 0
    assert wave["total_auc"] == 4
    assert wave["auc_at_peak"] == 3
    assert wave["accumulation_rate"] == 1
    assert wave["centroid_time"] == 1
    assert wave["half_accumulation_time"] == 1


def test_numeric_and_column_thresholds() -> None:
    df = pd.DataFrame(
        {
            "signal": [1.0, 2.0, 3.0],
            "baseline": [0.5, 1.0, 1.5],
            "signal_wave_id": [1, 1, 1],
            "signal_peak": [False, True, False],
        }
    )

    numeric = Accumulation("signal", threshold=1).fit_transform(df)
    column = Accumulation("signal", threshold="baseline").fit_transform(df)

    assert numeric["signal_accumulation_threshold"].tolist() == [1.0] * 3
    assert column["signal_accumulation_threshold"].tolist() == [0.5, 1.0, 1.5]


def test_threshold_mapping_requires_every_signal() -> None:
    behavior = Accumulation(
        ["signal", "other"],
        threshold={"signal": "min"},
    )

    with pytest.raises(ValueError, match="No threshold"):
        behavior.threshold_for("other")


def test_accumulation_requires_peak_event(
    triangular_signal: pd.DataFrame,
) -> None:
    features = oscillation_features(triangular_signal).drop(
        columns="signal_peak"
    )
    behavior = Accumulation("signal")

    with pytest.raises(ValueError, match="peak event column"):
        behavior.fit_transform(features)
