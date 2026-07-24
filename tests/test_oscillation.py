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
