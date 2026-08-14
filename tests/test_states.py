import pandas as pd
from pandas.testing import assert_series_equal

from featuregraph.operators.states import (
    accumulating_state,
    depleting_state,
    falling_state,
    hysteresis_state,
    inactive_state,
    negative_state,
    positive_state,
    rising_state,
)


def test_hysteresis_state_retains_state_in_neutral_band() -> None:
    quantity = pd.Series([0.0, 1.1, 0.8, 0.6, 0.4, 1.2])

    assert_series_equal(
        hysteresis_state(
            quantity,
            enter_eps=1.0,
            exit_eps=0.5,
        ),
        pd.Series([False, True, True, True, False, True]),
    )


def test_hysteresis_state_resets_between_groups() -> None:
    quantity = pd.Series([1.1, 0.8, 0.8, 1.1])
    group = pd.Series([1, 1, 2, 2])

    assert_series_equal(
        hysteresis_state(
            quantity,
            enter_eps=1.0,
            exit_eps=0.5,
            group=group,
        ),
        pd.Series([True, True, False, True]),
    )


def test_equal_hysteresis_thresholds_match_positive_state() -> None:
    quantity = pd.Series([float("nan"), 0.0, 0.1, 0.2])

    assert_series_equal(
        hysteresis_state(
            quantity,
            enter_eps=0.1,
            exit_eps=0.1,
        ),
        positive_state(quantity, eps=0.1),
    )


def test_level_states_respect_epsilon() -> None:
    quantity = pd.Series([-0.2, -0.1, 0.0, 0.1, 0.2])

    assert_series_equal(
        positive_state(quantity, eps=0.1),
        pd.Series([False, False, False, False, True]),
    )
    assert_series_equal(
        negative_state(quantity, eps=0.1),
        pd.Series([True, False, False, False, False]),
    )
    assert_series_equal(
        inactive_state(quantity, eps=0.1),
        pd.Series([False, True, True, True, False]),
    )


def test_directional_states_use_lagged_difference() -> None:
    quantity = pd.Series([0.0, 1.0, 3.0, 2.0, 0.0])

    assert_series_equal(
        rising_state(quantity, lag=2),
        pd.Series([False, False, True, True, False]),
    )
    assert_series_equal(
        falling_state(quantity, lag=2),
        pd.Series([False, False, False, False, True]),
    )


def test_accumulation_states_reuse_level_states() -> None:
    contribution = pd.Series([-1.0, 0.0, 1.0])

    assert_series_equal(
        accumulating_state(contribution),
        positive_state(contribution),
    )
    assert_series_equal(
        depleting_state(contribution),
        negative_state(contribution),
    )
