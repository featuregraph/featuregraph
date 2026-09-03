"""state-contract-v2: derived columns and the exclude policy.

v1 is frozen. Every test here either exercises something v1 cannot express or
checks that v1 still refuses it.
"""

import numpy as np
import pandas as pd
import pytest

from featuregraph import StateContractError, compile_states

COLUMN = {"column": "signal"}


def _direction_states(column: str, eps: dict) -> dict:
    value = {"column": column}
    return {
        "rising": {"op": "gt", "left": value, "right": eps},
        "falling": {"op": "lt", "left": value, "right": {"op": "neg", "value": eps}},
        "inactive": {"op": "le", "left": {"op": "abs", "value": value}, "right": eps},
    }


def _envelope_contract(*, window: int = 3, group_by=None, policy="exclude") -> dict:
    """Rolling max, rolling mean, backward shift, then a first difference."""
    smooth = {
        "op": "shift",
        "value": {
            "op": "rolling_mean",
            "value": {
                "op": "rolling_max",
                "value": COLUMN,
                "window": {"parameter": "window"},
            },
            "window": {"parameter": "window"},
        },
        "periods": {"op": "neg", "value": {"parameter": "window"}},
    }
    contract = {
        "version": "state-contract-v2",
        "missing_policy": policy,
        "parameters": {"window": window, "atol": 1e-12},
        "derive": {
            "smooth": smooth,
            "change": {"op": "diff", "value": {"column": "smooth"}},
        },
        "states": _direction_states("change", {"parameter": "atol"}),
        "events": {
            "enter_rising": {"type": "enter_state", "state": "rising"},
            "exit_rising": {"type": "exit_state", "state": "rising"},
        },
        "boundary_policy": {"include_first_entry": True, "include_last_exit": False},
    }
    if group_by is not None:
        contract["group_by"] = group_by
    return contract


def _published_path(frame: pd.DataFrame, window: int, group: str | None):
    """What the BIDMC and TEP notebooks do: preprocess in pandas, compile v1."""
    grouped = frame.groupby(group)["signal"] if group else frame["signal"]

    def envelope(series: pd.Series) -> pd.Series:
        return (
            series.rolling(window, min_periods=window)
            .max()
            .rolling(window, min_periods=window)
            .mean()
            .shift(-window)
        )

    prepared = frame.copy()
    prepared["smooth"] = grouped.transform(envelope) if group else envelope(grouped)
    prepared["change"] = (
        prepared.groupby(group)["smooth"].diff() if group else prepared["smooth"].diff()
    )
    valid = prepared["change"].notna()
    v1 = {
        "version": "state-contract-v1",
        "parameters": {"atol": 1e-12},
        "states": _direction_states("change", {"parameter": "atol"}),
        "events": {
            "enter_rising": {"type": "enter_state", "state": "rising"},
            "exit_rising": {"type": "exit_state", "state": "rising"},
        },
        "boundary_policy": {"include_first_entry": True, "include_last_exit": False},
    }
    if group:
        v1["group_by"] = group
    return prepared, valid, compile_states(prepared.loc[valid], v1).observations


def _signal(seed: int, length: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(length)
    return np.sin(t / 7.0) + 0.3 * np.sin(t / 2.3) + 0.05 * rng.standard_normal(length)


# -- derive ---------------------------------------------------------------


def test_derived_columns_match_pandas_and_respect_groups():
    frame = pd.DataFrame(
        {
            "record": ["a"] * 8 + ["b"] * 8,
            "signal": np.r_[_signal(1, 8), _signal(2, 8)],
        }
    )
    contract = _envelope_contract(window=2, group_by="record")

    result = compile_states(frame, contract)
    prepared, _, _ = _published_path(frame, 2, "record")

    assert result.observations["smooth"].equals(prepared["smooth"])
    assert result.observations["change"].equals(prepared["change"])
    assert list(frame.columns) == ["record", "signal"], "input not mutated"
    derived = result.validation_report.set_index("check").loc["derived_columns"]
    assert derived["details"] == "columns=['smooth', 'change']"


def test_window_and_periods_accept_integers_or_scalar_expressions():
    frame = pd.DataFrame({"signal": [1.0, 2.0, 4.0, 7.0]})
    contract = {
        "version": "state-contract-v2",
        "missing_policy": "exclude",
        "parameters": {"lag": 2},
        "derive": {
            "lagged": {"op": "shift", "value": COLUMN, "periods": {"parameter": "lag"}},
            "step": {"op": "diff", "value": COLUMN, "periods": 1},
            "mean2": {
                "op": "rolling_mean",
                "value": COLUMN,
                "window": 2,
                "min_periods": 1,
            },
        },
        "states": {
            "any": {"op": "ge", "left": {"column": "step"}, "right": {"literal": 0}}
        },
    }

    observations = compile_states(frame, contract).observations

    assert observations["lagged"].tolist()[2:] == [1.0, 2.0]
    assert observations["mean2"].tolist() == [1.0, 1.5, 3.0, 5.5]
    assert observations["state_valid"].tolist() == [False, True, True, True]


def test_arithmetic_derives_a_rate_from_two_columns():
    frame = pd.DataFrame({"signal": [0.0, 1.0, 3.0], "hours": [0.0, 0.5, 1.5]})
    contract = {
        "version": "state-contract-v2",
        "missing_policy": "exclude",
        "derive": {
            "rate": {
                "op": "div",
                "left": {"op": "diff", "value": COLUMN},
                "right": {"op": "diff", "value": {"column": "hours"}},
            }
        },
        "states": {
            "moving": {"op": "gt", "left": {"column": "rate"}, "right": {"literal": 0}}
        },
    }

    observations = compile_states(frame, contract).observations

    assert observations["rate"].tolist()[1:] == [2.0, 2.0]
    assert observations["state"].tolist() == [None, "moving", "moving"]


@pytest.mark.parametrize(
    "contract",
    [
        {
            "version": "state-contract-v1",
            "derive": {"x": {"op": "diff", "value": COLUMN}},
            "states": {"a": {"op": "gt", "left": COLUMN, "right": {"literal": 0}}},
        },
        {
            "version": "state-contract-v1",
            "states": {
                "a": {
                    "op": "gt",
                    "left": {"op": "diff", "value": COLUMN},
                    "right": {"literal": 0},
                }
            },
        },
        {
            "version": "state-contract-v1",
            "missing_policy": "exclude",
            "states": {"a": {"op": "gt", "left": COLUMN, "right": {"literal": 0}}},
        },
    ],
)
def test_v1_refuses_everything_v2_added(contract):
    with pytest.raises(StateContractError) as caught:
        compile_states(pd.DataFrame({"signal": [1.0, 2.0]}), contract)

    assert caught.value.code in {"operator_requires_v2", "malformed_contract"}


@pytest.mark.parametrize("name", ["signal", "state", "state__x", "state_valid"])
def test_derived_names_cannot_shadow_inputs_or_compiler_output(name):
    contract = {
        "version": "state-contract-v2",
        "derive": {name: {"op": "diff", "value": COLUMN}},
        "states": {"a": {"op": "ge", "left": COLUMN, "right": {"literal": 0}}},
    }

    with pytest.raises(StateContractError) as caught:
        compile_states(pd.DataFrame({"signal": [1.0, 2.0]}), contract)

    assert caught.value.code == "derived_column_collision"
    assert caught.value.locus == {"column": name}


def test_window_operator_refuses_a_scalar():
    contract = {
        "version": "state-contract-v2",
        "derive": {"x": {"op": "rolling_max", "value": {"literal": 1}, "window": 2}},
        "states": {"a": {"op": "ge", "left": COLUMN, "right": {"literal": 0}}},
    }

    with pytest.raises(StateContractError, match="not a scalar"):
        compile_states(pd.DataFrame({"signal": [1.0, 2.0]}), contract)


# -- missing_policy -------------------------------------------------------


def test_error_policy_names_the_derived_column_that_is_missing():
    frame = pd.DataFrame({"signal": _signal(3, 12)})

    with pytest.raises(StateContractError) as caught:
        compile_states(frame, _envelope_contract(window=3, policy="error"))

    assert caught.value.code == "missing_values_in_input"
    assert caught.value.locus["column"] == "change"


def test_exclude_keeps_every_row_and_reports_where_the_gaps_are():
    frame = pd.DataFrame({"signal": _signal(4, 12)})
    frame.loc[7, "signal"] = np.nan  # an interior gap in the source

    result = compile_states(frame, _envelope_contract(window=2))
    observations = result.observations

    assert len(observations) == len(frame)
    assert observations["state_valid"].dtype == bool
    invalid = ~observations["state_valid"]
    assert observations.loc[invalid, "state"].isna().all()
    assert observations.loc[invalid, "state_occurrence_id"].isna().all()
    assert observations["state_occurrence_id"].dtype == "Int64"
    assert not observations.loc[invalid, "enter_rising"].any()
    assert not observations.loc[invalid, "state__rising"].any()
    report = result.validation_report.set_index("check")
    # smooth needs two full windows and a shift of 2: rows 0-2 and the last
    # two are undefined, diff drops one more, and the NaN at 7 spreads.
    assert report.loc["invalid_observations", "details"].startswith("excluded=")
    assert "interior=" in report.loc["invalid_observations", "details"]
    counts = dict(
        part.split("=")
        for part in report.loc["invalid_observations", "details"].split()
    )
    assert int(counts["excluded"]) == int(invalid.sum())
    assert int(counts["interior"]) > 0


def test_exclude_does_not_split_an_occurrence_across_an_interior_gap():
    frame = pd.DataFrame({"label": ["a", "a", None, "a", "b"]})
    contract = {
        "version": "state-contract-v2",
        "missing_policy": "exclude",
        "state_column": "label",
    }

    observations = compile_states(frame, contract).observations

    assert observations["state_occurrence_id"].tolist() == [0, 0, pd.NA, 0, 1]
    assert observations["state_valid"].tolist() == [True, True, False, True, True]


def test_exclude_counts_edges_per_group():
    frame = pd.DataFrame(
        {
            "record": ["a", "a", "a", "b", "b", "b"],
            "label": [None, "x", "x", "y", None, None],
        }
    )
    contract = {
        "version": "state-contract-v2",
        "missing_policy": "exclude",
        "group_by": "record",
        "state_column": "label",
    }

    report = compile_states(frame, contract).validation_report.set_index("check")

    assert (
        report.loc["invalid_observations", "details"]
        == "excluded=3 leading=1 trailing=2 interior=0"
    )


def test_exclude_refuses_to_compile_nothing():
    frame = pd.DataFrame({"label": [None, None]})
    contract = {
        "version": "state-contract-v2",
        "missing_policy": "exclude",
        "state_column": "label",
    }

    with pytest.raises(StateContractError) as caught:
        compile_states(frame, contract)

    assert caught.value.code == "no_valid_observations"


def test_v1_report_has_no_new_rows():
    contract = {
        "version": "state-contract-v1",
        "states": {"a": {"op": "ge", "left": COLUMN, "right": {"literal": 0}}},
    }

    report = compile_states(pd.DataFrame({"signal": [1.0]}), contract).validation_report

    assert report["check"].tolist() == [
        "exclusive_states",
        "exhaustive_states",
        "referenced_inputs",
        "occurrence_reconstruction",
        "event_references",
    ]


# -- equivalence with the published construction --------------------------


@pytest.mark.parametrize("group", [None, "record"])
def test_in_contract_derivation_reproduces_preprocess_then_compile(group):
    """The BIDMC construction, expressed entirely in the contract.

    The published notebook builds the envelope in pandas and compiles the
    difference under v1 on the valid rows. A v2 contract carrying the same
    derivation must produce the same states, occurrences, and events on the
    same rows, and nothing anywhere else.
    """
    frame = pd.DataFrame(
        {
            "record": ["a"] * 60 + ["b"] * 45,
            "signal": np.r_[_signal(5, 60), _signal(6, 45)],
        }
    )
    if group is None:
        frame = frame[frame["record"] == "a"].reset_index(drop=True)
    window = 4

    _, valid, published = _published_path(frame, window, group)
    declared = compile_states(frame, _envelope_contract(window=window, group_by=group))
    observations = declared.observations

    assert observations["state_valid"].equals(valid)
    on_valid = observations.loc[valid]
    assert on_valid["state"].tolist() == published["state"].tolist()
    assert (
        on_valid["state_occurrence_id"]
        .astype("int64")
        .equals(published["state_occurrence_id"])
    )
    for column in ("enter_rising", "exit_rising", "state__rising", "state__falling"):
        assert on_valid[column].equals(published[column]), column
    assert not observations.loc[~valid, ["enter_rising", "exit_rising"]].any().any()
    assert declared.validation_report["passed"].all()
