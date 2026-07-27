import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from featuregraph.behaviors.transition import Transition


def test_transition_constructs_all_three_directions() -> None:
    df = pd.DataFrame(
        {
            "signal": [
                0.0,
                1.0,
                2.0,
                2.0,
                1.0,
                0.0,
            ]
        }
    )

    behavior = Transition("signal", diff_lag=1)
    result = behavior.fit_transform(df)

    assert result["signal_rising"].tolist() == [
        False,
        True,
        True,
        False,
        False,
        False,
    ]
    assert result["signal_inactive"].tolist() == [
        False,
        False,
        False,
        True,
        False,
        False,
    ]
    assert result["signal_falling"].tolist() == [
        False,
        False,
        False,
        False,
        True,
        True,
    ]
    assert pd.isna(result.loc[0, "signal_transition_direction"])
    assert result["signal_transition_direction"].iloc[1:].tolist() == [
        "rising",
        "rising",
        "inactive",
        "falling",
        "falling",
    ]


def test_transition_summary_returns_directional_objects() -> None:
    df = pd.DataFrame(
        {"signal": [0.0, 1.0, 2.0, 2.0, 1.0, 0.0]}
    )
    behavior = Transition("signal", diff_lag=1)
    features = behavior.fit_transform(df)

    objects = behavior.summarize(
        features,
        "signal",
        include_partial=True,
    )

    assert objects.behavior_type == "transition"
    assert objects.table["direction"].tolist() == [
        "rising",
        "inactive",
        "falling",
    ]
    assert objects.table["start_index"].tolist() == [0.0, 2.0, 3.0]
    assert objects.table["end_index"].tolist() == [2.0, 3.0, 5.0]
    assert objects.table["is_complete"].tolist() == [
        True,
        True,
        False,
    ]


def test_transition_resets_at_group_boundaries() -> None:
    df = pd.DataFrame(
        {
            "group": ["a", "a", "a", "b", "b", "b"],
            "signal": [0.0, 1.0, 2.0, 10.0, 11.0, 12.0],
        }
    )
    result = Transition(
        "signal",
        group="group",
        diff_lag=1,
    ).fit_transform(df)

    first_rows = result.groupby("group", sort=False).head(1)
    assert first_rows["signal_difference"].isna().all()
    assert first_rows["signal_transition_id"].eq(0).all()


def test_transition_does_not_mutate_input() -> None:
    df = pd.DataFrame({"signal": [0.0, 1.0, 2.0]})
    original = df.copy()

    Transition("signal", diff_lag=1).fit_transform(df)

    assert_frame_equal(df, original)


def test_transition_eps_controls_inactive_state() -> None:
    df = pd.DataFrame({"signal": [0.0, 0.05, 0.2]})

    result = Transition(
        "signal",
        diff_lag=1,
        eps=0.1,
    ).fit_transform(df)

    assert result["signal_inactive"].tolist() == [
        False,
        True,
        False,
    ]
    assert result["signal_rising"].tolist() == [
        False,
        False,
        True,
    ]


def test_transition_summary_excludes_right_partial_by_default() -> None:
    df = pd.DataFrame(
        {"signal": [0.0, 1.0, 2.0, 2.0, 1.0, 0.0]}
    )
    behavior = Transition("signal", diff_lag=1)
    features = behavior.fit_transform(df)

    complete = behavior.summarize(features, "signal").table
    all_objects = behavior.summarize(
        features,
        "signal",
        include_partial=True,
    ).table

    assert complete["direction"].tolist() == [
        "rising",
        "inactive",
    ]
    assert all_objects["is_complete"].tolist() == [
        True,
        True,
        False,
    ]


def test_transition_measurements_use_segment_boundaries() -> None:
    df = pd.DataFrame(
        {"signal": [0.0, 1.0, 2.0, 2.0, 1.0, 0.0]}
    )
    behavior = Transition("signal", diff_lag=1)
    features = behavior.fit_transform(df)
    table = behavior.summarize(
        features,
        "signal",
        include_partial=True,
    ).table

    rising, inactive, falling = (
        table.set_index("direction").loc[
            ["rising", "inactive", "falling"]
        ].itertuples()
    )

    assert (rising.start_value, rising.end_value) == (0.0, 2.0)
    assert rising.net_change == 2.0
    assert rising.duration == 2.0
    assert rising.mean_rate == 1.0
    assert (inactive.start_value, inactive.end_value) == (2.0, 2.0)
    assert inactive.net_change == 0.0
    assert (falling.start_value, falling.end_value) == (2.0, 0.0)
    assert falling.net_change == -2.0


def test_transition_missing_value_breaks_directional_continuity() -> None:
    df = pd.DataFrame(
        {"signal": [0.0, 1.0, 2.0, float("nan"), 3.0, 4.0]}
    )
    result = Transition(
        "signal",
        diff_lag=1,
    ).fit_transform(df)

    assert pd.isna(result.loc[3, "signal_transition_direction"])
    assert pd.isna(result.loc[4, "signal_transition_direction"])
    assert result.loc[5, "signal_transition_direction"] == "rising"
    assert result.loc[5, "signal_transition_id"] == 2


def test_transition_constructs_multiple_signals_independently() -> None:
    df = pd.DataFrame(
        {
            "signal": [0.0, 1.0, 2.0, 1.0],
            "other": [2.0, 1.0, 0.0, 1.0],
        }
    )
    result = Transition(
        ["signal", "other"],
        diff_lag=1,
    ).fit_transform(df)

    assert result.loc[1, "signal_transition_direction"] == "rising"
    assert result.loc[1, "other_transition_direction"] == "falling"
    assert "signal_transition_id" in result
    assert "other_transition_id" in result


def test_transition_resets_multi_column_groups() -> None:
    df = pd.DataFrame(
        {
            "subject": ["a"] * 3 + ["a"] * 3,
            "run": [1] * 3 + [2] * 3,
            "signal": [0.0, 1.0, 2.0, 10.0, 11.0, 12.0],
        }
    )
    result = Transition(
        "signal",
        group=["subject", "run"],
        diff_lag=1,
    ).fit_transform(df)

    first_rows = result.groupby(
        ["subject", "run"],
        sort=False,
    ).head(1)
    assert first_rows["signal_difference"].isna().all()
    assert first_rows["signal_transition_id"].eq(0).all()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"diff_lag": 0}, "diff_lag"),
        ({"eps": -0.1}, "eps"),
    ],
)
def test_transition_rejects_invalid_sensitivity(
    kwargs: dict[str, float],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        Transition("signal", **kwargs)


def test_transition_summary_rejects_unconfigured_signal() -> None:
    behavior = Transition("signal", diff_lag=1)
    features = behavior.fit_transform(
        pd.DataFrame({"signal": [0.0, 1.0]})
    )

    with pytest.raises(ValueError, match="was not configured"):
        behavior.summarize(features, "other")


def test_transition_supports_non_default_index_labels() -> None:
    df = pd.DataFrame(
        {"signal": [0.0, 1.0, 2.0, 1.0]},
        index=["a", "b", "c", "d"],
    )
    behavior = Transition("signal", diff_lag=1)
    features = behavior.fit_transform(df)
    table = behavior.summarize(
        features,
        "signal",
        include_partial=True,
    ).table

    assert table["start_index"].tolist() == ["a", "c"]
    assert table["end_index"].tolist() == ["c", "d"]
    assert table["duration_samples"].tolist() == [2.0, 1.0]


def test_transition_uses_elapsed_time_for_duration_and_rate() -> None:
    df = pd.DataFrame(
        {
            "time": [0.0, 1.0, 3.0, 6.0],
            "signal": [0.0, 1.0, 2.0, 1.0],
        }
    )
    behavior = Transition(
        "signal",
        diff_lag=1,
        time="time",
    )
    features = behavior.fit_transform(df)
    table = behavior.summarize(
        features,
        "signal",
        include_partial=True,
    ).table

    rising = table.loc[table["direction"].eq("rising")].iloc[0]
    assert rising["duration_samples"] == 2
    assert rising["duration"] == 3
    assert rising["mean_rate"] == pytest.approx(2 / 3)
    assert rising["peak_rate"] == 1
