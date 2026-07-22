import pandas as pd
from pandas.testing import assert_series_equal

from featuregraph.operators.events import (
    enter_state,
    event_id,
    event_index,
    exit_state,
)


def test_enter_and_exit_state() -> None:
    state = pd.Series([False, True, True, False, True])

    assert_series_equal(
        enter_state(state),
        pd.Series([False, True, False, False, True]),
    )
    assert_series_equal(
        exit_state(state),
        pd.Series([False, False, False, True, False]),
    )


def test_enter_and_exit_reset_at_group_boundaries() -> None:
    state = pd.Series([False, True, True, False])
    group = pd.Series(["a", "a", "b", "b"])

    assert_series_equal(
        enter_state(state, group),
        pd.Series([False, True, False, False]),
    )
    assert_series_equal(
        exit_state(state, group),
        pd.Series([False, False, False, True]),
    )


def test_event_id_resets_for_each_group() -> None:
    df = pd.DataFrame(
        {
            "group": ["a", "a", "b", "b"],
            "enter": [False, True, False, True],
        }
    )

    assert_series_equal(
        event_id(df, "enter", group="group"),
        pd.Series([0, 1, 0, 1]),
        check_names=False,
    )


def test_event_index_preserves_index_and_resets_by_group() -> None:
    df = pd.DataFrame(
        {
            "group": ["a", "a", "b", "b"],
            "event": [False, True, False, True],
        },
        index=[10, 11, 20, 21],
    )

    result = event_index(df, "event", group="group")

    assert_series_equal(
        result,
        pd.Series([float("nan"), 11.0, float("nan"), 21.0], index=df.index),
    )
