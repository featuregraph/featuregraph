"""Compile declarative state contracts into states, events, and occurrences."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from functools import reduce
from operator import and_, or_
from typing import Any, Mapping

import pandas as pd

from featuregraph.operators.events import enter_label, exit_label


class StateContractError(ValueError):
    """Raised when a state contract is invalid or fails declared validation."""


@dataclass(frozen=True)
class CompiledStateResult:
    """Deterministic output of a state contract compilation."""

    observations: pd.DataFrame
    validation_report: pd.DataFrame
    contract: dict[str, Any]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise StateContractError(message)


def _group_keys(df: pd.DataFrame, group_by: list[str]) -> Any:
    if not group_by:
        return None
    if len(group_by) == 1:
        return df[group_by[0]]
    return [df[column] for column in group_by]


def _sample_indices(mask: pd.Series, limit: int = 5) -> list[Any]:
    return mask.index[mask].tolist()[:limit]


class _ExpressionEvaluator:
    def __init__(
        self,
        observations: pd.DataFrame,
        parameters: Mapping[str, Any],
        missing_policy: str,
    ) -> None:
        self.observations = observations
        self.parameters = parameters
        self.missing_policy = missing_policy
        self.referenced_columns: set[str] = set()

    def evaluate(self, expression: Any) -> Any:
        _require(
            isinstance(expression, Mapping),
            "Every state expression must be a mapping.",
        )
        keys = set(expression)
        if keys == {"column"}:
            column = expression["column"]
            _require(isinstance(column, str), "Column references must be strings.")
            _require(column in self.observations, f"Unknown input column: {column!r}.")
            values = self.observations[column]
            self.referenced_columns.add(column)
            if self.missing_policy == "error" and values.isna().any():
                samples = _sample_indices(values.isna())
                raise StateContractError(
                    f"Input column {column!r} contains missing values at {samples}."
                )
            return values
        if keys == {"parameter"}:
            parameter = expression["parameter"]
            _require(
                isinstance(parameter, str), "Parameter references must be strings."
            )
            _require(
                parameter in self.parameters,
                f"Unknown contract parameter: {parameter!r}.",
            )
            return self.parameters[parameter]
        if keys == {"literal"}:
            return expression["literal"]

        op = expression.get("op")
        _require(isinstance(op, str), "Expression must contain one known 'op'.")
        if op in {"abs", "neg", "not"}:
            _require(
                keys == {"op", "value"},
                f"Unary operator {op!r} requires only 'op' and 'value'.",
            )
            value = self.evaluate(expression["value"])
            if op == "abs":
                return abs(value)
            if op == "neg":
                return -value
            return ~self._as_boolean(value, "not operand")

        if op in {"and", "or"}:
            _require(
                keys == {"op", "values"},
                f"Boolean operator {op!r} requires only 'op' and 'values'.",
            )
            values = expression["values"]
            _require(
                isinstance(values, list) and len(values) >= 2,
                f"Boolean operator {op!r} requires at least two values.",
            )
            evaluated = [
                self._as_boolean(self.evaluate(value), f"{op} operand")
                for value in values
            ]
            return reduce(and_ if op == "and" else or_, evaluated)

        comparisons = {
            "gt": lambda left, right: left > right,
            "ge": lambda left, right: left >= right,
            "lt": lambda left, right: left < right,
            "le": lambda left, right: left <= right,
            "eq": lambda left, right: left == right,
            "ne": lambda left, right: left != right,
        }
        _require(op in comparisons, f"Unknown expression operator: {op!r}.")
        _require(
            keys == {"op", "left", "right"},
            f"Comparison {op!r} requires only 'op', 'left', and 'right'.",
        )
        return comparisons[op](
            self.evaluate(expression["left"]),
            self.evaluate(expression["right"]),
        )

    def _as_boolean(self, value: Any, context: str) -> pd.Series:
        _require(
            isinstance(value, pd.Series),
            f"{context.capitalize()} must evaluate to a boolean Series.",
        )
        _require(
            pd.api.types.is_bool_dtype(value.dtype),
            f"{context.capitalize()} must evaluate to boolean values.",
        )
        return value.astype(bool)


def _normalize_group_by(contract: Mapping[str, Any], df: pd.DataFrame) -> list[str]:
    raw_group_by = contract.get("group_by", [])
    if isinstance(raw_group_by, str):
        group_by = [raw_group_by]
    else:
        _require(isinstance(raw_group_by, list), "'group_by' must be a string or list.")
        group_by = raw_group_by
    _require(
        all(isinstance(column, str) for column in group_by),
        "Every 'group_by' entry must be a column name.",
    )
    missing = [column for column in group_by if column not in df]
    _require(not missing, f"Unknown grouping columns: {missing}.")
    return group_by


def _validation_row(check: str, passed: bool, details: str) -> dict[str, Any]:
    return {"check": check, "passed": passed, "details": details}


def compile_states(
    observations: pd.DataFrame, contract: Mapping[str, Any]
) -> CompiledStateResult:
    """Compile a declarative contract without mutating the input observations.

    A contract supplies either named boolean ``states`` or an existing
    categorical ``state_column``. It may also declare enter and exit events.
    Scientific preprocessing and interpretation remain outside this compiler.
    """
    _require(
        isinstance(observations, pd.DataFrame), "Observations must be a DataFrame."
    )
    _require(isinstance(contract, Mapping), "Contract must be a mapping.")
    frozen_contract = deepcopy(dict(contract))
    _require(
        frozen_contract.get("version") == "state-contract-v1",
        "Contract 'version' must be 'state-contract-v1'.",
    )
    missing_policy = frozen_contract.get("missing_policy", "error")
    _require(missing_policy == "error", "Only missing_policy='error' is supported.")
    output = observations.copy(deep=True)
    group_by = _normalize_group_by(frozen_contract, output)
    group_keys = _group_keys(output, group_by)

    states = frozen_contract.get("states")
    state_column = frozen_contract.get("state_column")
    _require(
        (states is None) != (state_column is None),
        "Declare exactly one of 'states' or 'state_column'.",
    )
    report: list[dict[str, Any]] = []

    if states is not None:
        _require(
            isinstance(states, Mapping) and bool(states),
            "'states' must be a non-empty mapping.",
        )
        _require(
            all(isinstance(name, str) and name for name in states),
            "State names must be non-empty strings.",
        )
        evaluator = _ExpressionEvaluator(
            output, frozen_contract.get("parameters", {}), missing_policy
        )
        masks: dict[str, pd.Series] = {}
        for name, expression in states.items():
            value = evaluator.evaluate(expression)
            masks[name] = evaluator._as_boolean(value, f"state {name!r}")
            output[f"state__{name}"] = masks[name]
        count = pd.concat(masks, axis=1).sum(axis=1)
        validation = frozen_contract.get("validation", {})
        _require(isinstance(validation, Mapping), "'validation' must be a mapping.")
        exclusive = validation.get("exclusive", True)
        exhaustive = validation.get("exhaustive", True)
        _require(isinstance(exclusive, bool), "'exclusive' must be boolean.")
        _require(isinstance(exhaustive, bool), "'exhaustive' must be boolean.")
        overlap = count.gt(1)
        gap = count.eq(0)
        report.append(
            _validation_row(
                "exclusive_states",
                not overlap.any(),
                f"overlap_rows={int(overlap.sum())}",
            )
        )
        report.append(
            _validation_row(
                "exhaustive_states", not gap.any(), f"gap_rows={int(gap.sum())}"
            )
        )
        if exclusive and overlap.any():
            raise StateContractError(
                f"States overlap at observation indices {_sample_indices(overlap)}."
            )
        if exhaustive and gap.any():
            raise StateContractError(
                f"No state is active at observation indices {_sample_indices(gap)}."
            )
        # Object dtype keeps boundary comparisons two-valued. Pandas' nullable
        # string dtype propagates NA through the first shift comparison.
        compiled_state = pd.Series(None, index=output.index, dtype="object")
        for name, mask in masks.items():
            compiled_state.loc[mask & compiled_state.isna()] = name
        output["state"] = compiled_state
        report.append(
            _validation_row(
                "referenced_inputs",
                True,
                f"columns={sorted(evaluator.referenced_columns)}",
            )
        )
        declared_labels: set[Any] | None = set(states)
    else:
        _require(isinstance(state_column, str), "'state_column' must be a string.")
        _require(state_column in output, f"Unknown state column: {state_column!r}.")
        missing = output[state_column].isna()
        if missing.any():
            raise StateContractError(
                f"State column {state_column!r} contains missing values at "
                f"{_sample_indices(missing)}."
            )
        output["state"] = output[state_column]
        report.append(
            _validation_row("external_state_complete", True, f"column={state_column!r}")
        )
        declared_labels = None

    boundary = frozen_contract.get("boundary_policy", {})
    _require(isinstance(boundary, Mapping), "'boundary_policy' must be a mapping.")
    include_first = boundary.get("include_first_entry", True)
    include_last = boundary.get("include_last_exit", True)
    _require(isinstance(include_first, bool), "'include_first_entry' must be boolean.")
    _require(isinstance(include_last, bool), "'include_last_exit' must be boolean.")

    structural_entries = enter_label(output["state"], group_keys, include_first=True)
    if group_by:
        output["state_occurrence_id"] = (
            structural_entries.groupby(group_keys, sort=False)
            .cumsum()
            .astype("int64")
            - 1
        )
    else:
        output["state_occurrence_id"] = structural_entries.cumsum().astype("int64") - 1

    events = frozen_contract.get("events", {})
    _require(isinstance(events, Mapping), "'events' must be a mapping.")
    entered = enter_label(output["state"], group_keys, include_first=include_first)
    exited = exit_label(output["state"], group_keys, include_last=include_last)
    for event_name, event in events.items():
        _require(
            isinstance(event_name, str) and event_name,
            "Event names must be non-empty strings.",
        )
        _require(isinstance(event, Mapping), f"Event {event_name!r} must be a mapping.")
        _require(
            isinstance(event.get("type"), str),
            f"Event {event_name!r} must contain a string 'type'.",
        )
        event_type = event["type"]
        _require(
            event_type
            in {"enter_state", "exit_state", "enter_label", "exit_label"},
            f"Unknown event type for {event_name!r}: {event_type!r}.",
        )
        if event_type in {"enter_label", "exit_label"}:
            _require(
                set(event) == {"type"},
                f"Event {event_name!r} of type {event_type!r} requires only 'type'.",
            )
            boundary_mask = entered if event_type == "enter_label" else exited
            output[event_name] = boundary_mask.astype(bool)
        else:
            _require(
                set(event) == {"type", "state"},
                f"Event {event_name!r} requires only 'type' and 'state'.",
            )
            label = event["state"]
            if declared_labels is not None:
                _require(
                    label in declared_labels,
                    f"Event {event_name!r} names undeclared state {label!r}.",
                )
            boundary_mask = entered if event_type == "enter_state" else exited
            output[event_name] = (
                boundary_mask & output["state"].eq(label)
            ).astype(bool)

    occurrence_groups: Any = [*group_by, "state_occurrence_id"]
    constant = (
        output.groupby(occurrence_groups, dropna=False)["state"]
        .nunique()
        .le(1)
        .all()
    )
    report.append(
        _validation_row(
            "occurrence_reconstruction",
            bool(constant),
            f"occurrences={output.groupby(occurrence_groups, dropna=False).ngroups}",
        )
    )
    _require(bool(constant), "Occurrence IDs do not reconstruct constant state runs.")
    report.append(_validation_row("event_references", True, f"events={len(events)}"))

    return CompiledStateResult(
        observations=output,
        validation_report=pd.DataFrame(report),
        contract=frozen_contract,
    )
