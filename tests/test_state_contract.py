import pandas as pd
import pytest

from featuregraph import StateContractError, compile_states


def _direction_contract():
    rate = {"column": "rate"}
    eps = {"parameter": "eps"}
    return {
        "version": "state-contract-v1",
        "parameters": {"eps": 0.1},
        "states": {
            "rising": {"op": "gt", "left": rate, "right": eps},
            "falling": {
                "op": "lt",
                "left": rate,
                "right": {"op": "neg", "value": eps},
            },
            "inactive": {
                "op": "le",
                "left": {"op": "abs", "value": rate},
                "right": eps,
            },
        },
        "events": {
            "enter_rising": {"type": "enter_state", "state": "rising"},
            "exit_rising": {"type": "exit_state", "state": "rising"},
        },
        "validation": {"exclusive": True, "exhaustive": True},
    }


def test_compiles_direction_states_events_and_occurrences():
    observations = pd.DataFrame({"rate": [-1.0, 0.0, 1.0, 1.0, -1.0]})

    result = compile_states(observations, _direction_contract())

    assert result.observations["state"].tolist() == [
        "falling",
        "inactive",
        "rising",
        "rising",
        "falling",
    ]
    assert result.observations["state_occurrence_id"].tolist() == [0, 1, 2, 2, 3]
    assert result.observations["enter_rising"].tolist() == [
        False,
        False,
        True,
        False,
        False,
    ]
    assert result.observations["exit_rising"].tolist() == [
        False,
        False,
        False,
        True,
        False,
    ]
    assert result.validation_report["passed"].all()
    assert list(observations.columns) == ["rate"]


def test_group_boundaries_reset_occurrence_ids_and_events():
    observations = pd.DataFrame(
        {"record": ["a", "a", "b", "b"], "label": [1, 1, 1, 0]}
    )
    contract = {
        "version": "state-contract-v1",
        "state_column": "label",
        "group_by": "record",
        "events": {
            "enter_one": {"type": "enter_state", "state": 1},
            "exit_one": {"type": "exit_state", "state": 1},
        },
    }

    result = compile_states(observations, contract).observations

    assert result["state_occurrence_id"].tolist() == [0, 0, 0, 1]
    assert result["enter_one"].tolist() == [True, False, True, False]
    assert result["exit_one"].tolist() == [False, True, True, False]


def test_boundary_policy_can_exclude_dataset_edges():
    observations = pd.DataFrame({"label": ["active", "active"]})
    contract = {
        "version": "state-contract-v1",
        "state_column": "label",
        "boundary_policy": {
            "include_first_entry": False,
            "include_last_exit": False,
        },
        "events": {
            "enter": {"type": "enter_state", "state": "active"},
            "exit": {"type": "exit_state", "state": "active"},
        },
    }

    result = compile_states(observations, contract).observations

    assert not result["enter"].any()
    assert not result["exit"].any()
    assert result["state_occurrence_id"].tolist() == [0, 0]


@pytest.mark.parametrize(
    ("states", "message"),
    [
        (
            {
                "positive": {
                    "op": "ge",
                    "left": {"column": "x"},
                    "right": {"literal": 0},
                },
                "nonnegative": {
                    "op": "ge",
                    "left": {"column": "x"},
                    "right": {"literal": 0},
                },
            },
            "overlap",
        ),
        (
            {
                "positive": {
                    "op": "gt",
                    "left": {"column": "x"},
                    "right": {"literal": 0},
                },
                "negative": {
                    "op": "lt",
                    "left": {"column": "x"},
                    "right": {"literal": 0},
                },
            },
            "No state",
        ),
    ],
)
def test_rejects_overlapping_or_incomplete_state_partitions(states, message):
    contract = {"version": "state-contract-v1", "states": states}

    with pytest.raises(StateContractError, match=message):
        compile_states(pd.DataFrame({"x": [0]}), contract)


@pytest.mark.parametrize(
    ("contract", "message"),
    [
        (
            {
                "version": "state-contract-v1",
                "states": {
                    "a": {
                        "op": "gt",
                        "left": {"column": "missing"},
                        "right": {"literal": 0},
                    }
                },
            },
            "Unknown input column",
        ),
        (
            {
                "version": "state-contract-v1",
                "states": {
                    "a": {
                        "op": "mystery",
                        "left": {"column": "x"},
                        "right": {"literal": 0},
                    }
                },
            },
            "Unknown expression operator",
        ),
    ],
)
def test_contract_errors_are_explicit(contract, message):
    with pytest.raises(StateContractError, match=message):
        compile_states(pd.DataFrame({"x": [1]}), contract)


def test_rejects_missing_input_values():
    contract = _direction_contract()

    with pytest.raises(StateContractError, match="missing values"):
        compile_states(pd.DataFrame({"rate": [float("nan")]}), contract)


def test_contract_is_copied_into_result():
    contract = _direction_contract()
    result = compile_states(pd.DataFrame({"rate": [0.0]}), contract)

    contract["parameters"]["eps"] = 99

    assert result.contract["parameters"]["eps"] == 0.1


def _overlapping_contract():
    return {
        "version": "state-contract-v1",
        "states": {
            "low": {"op": "lt", "left": {"column": "x"}, "right": {"literal": 10}},
            "high": {"op": "gt", "left": {"column": "x"}, "right": {"literal": 1}},
        },
    }


def test_error_carries_a_code_and_locus_without_changing_its_message():
    contract = _overlapping_contract()

    with pytest.raises(StateContractError) as caught:
        compile_states(pd.DataFrame({"x": [5, 5]}), contract)

    error = caught.value
    assert error.code == "states_overlap"
    assert error.locus["observation_indices"] == [0, 1]
    # The message is unchanged; the fields are additional, not a replacement.
    assert str(error) == "States overlap at observation indices [0, 1]."
    assert isinstance(error, ValueError)


def test_gap_error_locates_the_unaccounted_observations():
    contract = {
        "version": "state-contract-v1",
        "states": {
            "high": {"op": "gt", "left": {"column": "x"}, "right": {"literal": 10}}
        },
    }

    with pytest.raises(StateContractError) as caught:
        compile_states(pd.DataFrame({"x": [1, 20]}), contract)

    assert caught.value.code == "states_not_exhaustive"
    assert caught.value.locus["observation_indices"] == [0]


def test_unknown_column_names_the_column_it_could_not_find():
    contract = {
        "version": "state-contract-v1",
        "states": {
            "a": {"op": "gt", "left": {"column": "absent"}, "right": {"literal": 0}}
        },
    }

    with pytest.raises(StateContractError) as caught:
        compile_states(pd.DataFrame({"x": [1]}), contract)

    assert caught.value.code == "unknown_column"
    assert caught.value.locus == {"column": "absent"}


def test_missing_input_values_are_a_data_failure_not_a_contract_failure():
    with pytest.raises(StateContractError) as caught:
        compile_states(pd.DataFrame({"rate": [float("nan")]}), _direction_contract())

    assert caught.value.code == "missing_values_in_input"
    assert caught.value.locus["column"] == "rate"


def test_shape_errors_default_to_a_malformed_contract_code():
    with pytest.raises(StateContractError) as caught:
        compile_states(pd.DataFrame({"x": [1]}), {"version": "wrong"})

    assert caught.value.code == "malformed_contract"
    assert caught.value.locus == {}
