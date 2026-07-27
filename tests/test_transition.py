import pandas as pd
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
