import pandas as pd

from featuregraph.behaviors.transition import Transition
from featuregraph.operators.states import falling_state, rising_state


def test_transition_materializes_rising_state_and_events() -> None:
    df = pd.DataFrame({"signal": [0.0, 1.0, 2.0, 1.0]})

    behavior = Transition(df, "signal", "rising", rising_state)

    assert behavior.df is df
    assert df["signal_rising"].tolist() == [False, True, True, False]
    assert df["enter_signal_rising"].tolist() == [False, True, False, False]
    assert df["exit_signal_rising"].tolist() == [False, False, False, True]
    assert df["signal_id"].tolist() == [0, 1, 1, 1]


def test_transition_materializes_falling_state() -> None:
    df = pd.DataFrame({"signal": [2.0, 1.0, 0.0, 1.0]})

    behavior = Transition(df, "signal", "falling", falling_state)

    assert behavior.state_col == "signal_falling"
    assert df["signal_falling"].tolist() == [False, True, True, False]


def test_transition_epsilon_rejects_floating_point_chatter() -> None:
    residue = 5.551115123125783e-17
    genuine_change = 9.7e-06
    df = pd.DataFrame(
        {
            "signal": [
                0.36,
                0.36 + residue,
                0.36,
                0.36 + genuine_change,
            ]
        }
    )

    Transition(
        df,
        "signal",
        "rising",
        rising_state,
        eps=1e-12,
    )

    assert df["signal_rising"].tolist() == [False, False, False, True]
    assert df["enter_signal_rising"].tolist() == [False, False, False, True]
    assert df["exit_signal_rising"].tolist() == [False, False, False, False]
    assert df["signal_id"].tolist() == [0, 0, 0, 1]


def test_transition_event_ids_reset_at_group_boundaries() -> None:
    df = pd.DataFrame(
        {
            "group": ["a", "a", "b", "b"],
            "signal": [0.0, 1.0, 0.0, 1.0],
        }
    )

    Transition(df, "signal", "rising", rising_state, group="group")

    assert df["enter_signal_rising"].tolist() == [False, True, False, True]
    assert df["signal_id"].tolist() == [0, 1, 0, 1]
