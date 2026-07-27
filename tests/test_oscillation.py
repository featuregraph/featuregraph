import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal, assert_series_equal

from featuregraph.behaviors.oscillation import Oscillation


def test_fit_transform_constructs_expected_primitives(
    triangular_signal: pd.DataFrame,
) -> None:
    behavior = Oscillation("signal", diff_lag=1)

    result = behavior.fit_transform(triangular_signal)

    assert_series_equal(
        result["signal_wave_id"],
        pd.Series([0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3], name="signal_wave_id"),
    )
    assert result["enter_signal_rising"].sum() == 3
    assert result["exit_signal_rising"].sum() == 3
    assert "signal_transition_id" in result
    assert set(
        result["signal_transition_direction"].dropna()
    ) == {"rising", "falling"}
    assert result.loc[2, "signal_peak"]
    assert result.loc[2, "signal_peak_index"] == 2
    assert result.loc[4, "signal_trough"]
    assert result.loc[5, "signal_trough_index"] == 4


def test_fit_transform_does_not_mutate_input(
    triangular_signal: pd.DataFrame,
) -> None:
    original = triangular_signal.copy()

    Oscillation("signal", diff_lag=1).fit_transform(
        triangular_signal
    )

    assert_frame_equal(triangular_signal, original)


def test_summary_returns_complete_objects_by_default(
    triangular_signal: pd.DataFrame,
) -> None:
    behavior = Oscillation("signal", diff_lag=1)
    features = behavior.fit_transform(triangular_signal)

    objects = behavior.summarize(features, "signal")
    summary = objects.table

    assert objects.behavior_type == "oscillation"
    assert objects.signal == "signal"
    assert objects.features is features
    assert objects.count == 2
    assert summary["oscillation_id"].tolist() == [1, 2]
    assert summary["is_complete"].all()
    assert summary["rise_duration"].tolist() == [2, 2]
    assert summary["fall_duration"].tolist() == [2, 2]
    assert summary["duration"].tolist() == [4, 4]
    assert summary["start_index"].tolist() == [0, 4]
    assert summary["peak_index"].tolist() == [2, 6]
    assert summary["end_index"].tolist() == [4, 8]
    assert summary["amplitude"].tolist() == [1.0, 1.0]
    assert summary["temporal_symmetry"].tolist() == [1.0, 1.0]
    assert np.isnan(summary.loc[0, "period"])
    assert summary.loc[1, "period"] == 4


def test_summary_can_retain_partial_objects(
    triangular_signal: pd.DataFrame,
) -> None:
    behavior = Oscillation("signal", diff_lag=1)
    features = behavior.fit_transform(triangular_signal)

    objects = behavior.summarize(
        features,
        "signal",
        include_partial=True,
    )
    summary = objects.table

    assert objects.construction["include_partial"] is True
    assert summary["oscillation_id"].tolist() == [0, 1, 2, 3]
    assert summary["is_complete"].tolist() == [False, True, True, False]


def test_grouped_construction_resets_stateful_operations(
    grouped_triangular_signal: pd.DataFrame,
) -> None:
    behavior = Oscillation(
        "signal",
        group=["subject", "run"],
        diff_lag=1,
    )

    result = behavior.fit_transform(grouped_triangular_signal)

    first_rows = result.groupby(["subject", "run"], sort=False).head(1)
    assert first_rows["signal_rate"].isna().all()
    assert not first_rows["signal_rising"].any()
    assert not first_rows["signal_falling"].any()
    assert first_rows["signal_peak_index"].isna().all()
    assert first_rows["signal_wave_id"].tolist() == [0, 0]


def test_multiple_signals_are_constructed_independently(
    grouped_triangular_signal: pd.DataFrame,
) -> None:
    behavior = Oscillation(
        ["signal", "signal_2"],
        group="subject",
        diff_lag=1,
    )

    result = behavior.fit_transform(grouped_triangular_signal)

    for signal in behavior.signals:
        assert f"{signal}_wave_id" in result
        assert f"{signal}_amplitude" in result

    assert_series_equal(
        result["signal_wave_id"],
        result["signal_2_wave_id"].rename("signal_wave_id"),
    )


def test_smoothing_works_without_groups() -> None:
    df = pd.DataFrame({"signal": [1.0, 3.0, 5.0, 7.0]})
    behavior = Oscillation(
        "signal",
        smooth_signal=True,
        smooth_window=2,
        diff_lag=1,
    )

    result = behavior.fit_transform(df)

    assert_series_equal(
        result["signal_smooth"],
        pd.Series([np.nan, 2.0, 4.0, 6.0], name="signal_smooth"),
    )


def test_summary_rejects_unconfigured_signal(
    triangular_signal: pd.DataFrame,
) -> None:
    behavior = Oscillation("signal", diff_lag=1)
    features = behavior.fit_transform(triangular_signal)

    with pytest.raises(ValueError, match="was not configured"):
        behavior.summarize(features, "other")


def test_summary_uses_extrema_boundaries_across_flat_regions() -> None:
    df = pd.DataFrame(
        {
            "signal": [
                0.0,
                1.0,
                2.0,
                2.0,
                1.0,
                0.0,
                1.0,
                2.0,
                2.0,
                1.0,
                0.0,
            ]
        }
    )
    behavior = Oscillation("signal", diff_lag=1)
    features = behavior.fit_transform(df)

    summary = behavior.summarize(features, "signal").table

    assert summary.loc[0, "start_index"] == 0
    assert summary.loc[0, "peak_index"] == 2
    assert summary.loc[0, "end_index"] == 5
    assert summary.loc[0, "rise_duration"] == 2
    assert summary.loc[0, "fall_duration"] == 3
    assert summary.loc[0, "duration"] == 5


def test_oscillation_composes_complete_transition_objects() -> None:
    df = pd.DataFrame(
        {
            "signal": [
                0.0,
                1.0,
                2.0,
                2.0,
                1.0,
                0.0,
                1.0,
                2.0,
                2.0,
                1.0,
                0.0,
            ]
        }
    )
    behavior = Oscillation("signal", diff_lag=1)
    features = behavior.fit_transform(df)
    summary = behavior.summarize(features, "signal").table

    assert set(
        features["signal_transition_direction"].dropna()
    ) == {"rising", "falling", "inactive"}
    assert features["signal_transition_id"].is_monotonic_increasing
    assert summary["start_index"].tolist() == [0]
    assert summary["peak_index"].tolist() == [2]
    assert summary["end_index"].tolist() == [5]


def test_smoothing_transitions_use_the_working_signal() -> None:
    df = pd.DataFrame(
        {"signal": [0.0, 2.0, 4.0, 2.0, 0.0]}
    )
    behavior = Oscillation(
        "signal",
        smooth_signal=True,
        smooth_window=2,
        diff_lag=1,
    )
    features = behavior.fit_transform(df)

    expected = features["signal_smooth"].diff().gt(0)
    assert_series_equal(
        features["signal_rising"],
        expected.rename("signal_rising"),
    )


def test_oscillation_uses_time_for_durations_and_period() -> None:
    df = pd.DataFrame(
        {
            "time": [
                0.0,
                1.0,
                3.0,
                6.0,
                10.0,
                15.0,
                21.0,
                28.0,
                36.0,
            ],
            "signal": [
                0.0,
                1.0,
                2.0,
                1.0,
                0.0,
                1.0,
                2.0,
                1.0,
                0.0,
            ],
        },
        index=[f"sample-{index}" for index in range(9)],
    )
    behavior = Oscillation(
        "signal",
        diff_lag=1,
        time="time",
    )
    features = behavior.fit_transform(df)
    table = behavior.summarize(features, "signal").table

    assert table["start_index"].tolist() == ["sample-0"]
    assert table["duration_samples"].tolist() == [4]
    assert table["rise_duration"].tolist() == [3.0]
    assert table["fall_duration"].tolist() == [7.0]
