"""Compile declarative state contracts into states, events, and occurrences."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from functools import reduce
from operator import add, and_, mul, or_, sub, truediv
from typing import Any

import numpy as np
import pandas as pd

from featuregraph.operators.events import enter_label, exit_label

CONTRACT_V1 = "state-contract-v1"
CONTRACT_V2 = "state-contract-v2"
SUPPORTED_VERSIONS = (CONTRACT_V1, CONTRACT_V2)

#: Columns the compiler writes and a contract may therefore not derive.
RESERVED_COLUMNS = frozenset({"state", "state_occurrence_id", "state_valid"})
RESERVED_PREFIX = "state__"

_COMPARISONS: dict[str, Callable[[Any, Any], Any]] = {
    "gt": lambda left, right: left > right,
    "ge": lambda left, right: left >= right,
    "lt": lambda left, right: left < right,
    "le": lambda left, right: left <= right,
    "eq": lambda left, right: left == right,
    "ne": lambda left, right: left != right,
}
_ARITHMETIC: dict[str, Callable[[Any, Any], Any]] = {
    "add": add,
    "sub": sub,
    "mul": mul,
    "div": truediv,
}
_ROLLING = {"rolling_max": "max", "rolling_mean": "mean", "rolling_min": "min"}


class StateContractError(ValueError):
    """Raised when a state contract is invalid or fails declared validation.

    Carries a stable ``code`` and a ``locus`` mapping alongside the message, so a
    caller can act on a failure without parsing prose. The message text is
    unchanged and remains the human-readable account.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "malformed_contract",
        locus: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.locus: dict[str, Any] = dict(locus or {})


@dataclass(frozen=True)
class CompiledStateResult:
    """Deterministic output of a state contract compilation."""

    observations: pd.DataFrame
    validation_report: pd.DataFrame
    contract: dict[str, Any]


def _require(
    condition: bool,
    message: str,
    *,
    code: str = "malformed_contract",
    locus: Mapping[str, Any] | None = None,
) -> None:
    if not condition:
        raise StateContractError(message, code=code, locus=locus)


def _group_keys(df: pd.DataFrame, group_by: list[str]) -> Any:
    if not group_by:
        return None
    if len(group_by) == 1:
        return df[group_by[0]]
    return [df[column] for column in group_by]


def _sample_indices(mask: pd.Series, limit: int = 5) -> list[Any]:
    return mask.index[mask].tolist()[:limit]


def _is_integer(value: Any) -> bool:
    return isinstance(value, (int, np.integer)) and not isinstance(value, bool)


def _referenced_columns(expression: Any, found: set[str]) -> set[str]:
    """Collect every ``{"column": name}`` reference below an expression."""
    if isinstance(expression, Mapping):
        if set(expression) == {"column"} and isinstance(expression["column"], str):
            found.add(expression["column"])
        else:
            for value in expression.values():
                _referenced_columns(value, found)
    elif isinstance(expression, list):
        for value in expression:
            _referenced_columns(value, found)
    return found


class _ExpressionEvaluator:
    def __init__(
        self,
        observations: pd.DataFrame,
        parameters: Mapping[str, Any],
        missing_policy: str,
        *,
        version: str = CONTRACT_V1,
        group_keys: Any = None,
        check_missing: bool = True,
    ) -> None:
        self.observations = observations
        self.parameters = parameters
        self.missing_policy = missing_policy
        self.version = version
        self.group_keys = group_keys
        self.check_missing = check_missing
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
            _require(
                column in self.observations,
                f"Unknown input column: {column!r}.",
                code="unknown_column",
                locus={"column": column},
            )
            values = self.observations[column]
            self.referenced_columns.add(column)
            if (
                self.check_missing
                and self.missing_policy == "error"
                and values.isna().any()
            ):
                samples = _sample_indices(values.isna())
                raise StateContractError(
                    f"Input column {column!r} contains missing values at {samples}.",
                    code="missing_values_in_input",
                    locus={"column": column, "observation_indices": samples},
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
                code="unknown_parameter",
                locus={"parameter": parameter},
            )
            return self.parameters[parameter]
        if keys == {"literal"}:
            return expression["literal"]

        op = expression.get("op")
        _require(
            isinstance(op, str),
            "Expression must contain one known 'op'.",
            code="malformed_expression",
        )
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

        if op in _COMPARISONS:
            _require(
                keys == {"op", "left", "right"},
                f"Comparison {op!r} requires only 'op', 'left', and 'right'.",
            )
            return _COMPARISONS[op](
                self.evaluate(expression["left"]),
                self.evaluate(expression["right"]),
            )

        if op in _ARITHMETIC or op in _ROLLING or op in {"shift", "diff"}:
            return self._evaluate_v2(op, expression, keys)

        raise StateContractError(
            f"Unknown expression operator: {op!r}.",
            code="malformed_expression",
            locus={"op": op},
        )

    # -- state-contract-v2 operators -------------------------------------

    def _evaluate_v2(
        self, op: str, expression: Mapping[str, Any], keys: set[str]
    ) -> Any:
        _require(
            self.version == CONTRACT_V2,
            f"Operator {op!r} requires '{CONTRACT_V2}'.",
            code="operator_requires_v2",
            locus={"op": op},
        )
        if op in _ARITHMETIC:
            _require(
                keys == {"op", "left", "right"},
                f"Arithmetic {op!r} requires only 'op', 'left', and 'right'.",
            )
            return _ARITHMETIC[op](
                self.evaluate(expression["left"]),
                self.evaluate(expression["right"]),
            )
        if op in _ROLLING:
            _require(
                keys
                in (
                    {"op", "value", "window"},
                    {"op", "value", "window", "min_periods"},
                ),
                f"Window operator {op!r} requires 'op', 'value', 'window' and "
                "optionally 'min_periods'.",
            )
            series = self._as_series(self.evaluate(expression["value"]), op)
            window = self._as_count(expression["window"], f"{op} window")
            _require(window >= 1, f"{op} window must be at least 1.")
            min_periods = (
                self._as_count(expression["min_periods"], f"{op} min_periods")
                if "min_periods" in expression
                else window
            )
            _require(
                1 <= min_periods <= window,
                f"{op} min_periods must lie between 1 and the window.",
            )
            method = _ROLLING[op]

            def rolled(part: pd.Series) -> pd.Series:
                return getattr(part.rolling(window, min_periods=min_periods), method)()

            return self._within_groups(series, rolled)
        if op == "shift":
            _require(
                keys == {"op", "value", "periods"},
                "Operator 'shift' requires only 'op', 'value', and 'periods'.",
            )
            series = self._as_series(self.evaluate(expression["value"]), op)
            periods = self._as_count(expression["periods"], "shift periods")
            return self._within_groups(series, lambda part: part.shift(periods))
        _require(
            keys in ({"op", "value"}, {"op", "value", "periods"}),
            "Operator 'diff' requires 'op', 'value', and optionally 'periods'.",
        )
        series = self._as_series(self.evaluate(expression["value"]), op)
        periods = (
            self._as_count(expression["periods"], "diff periods")
            if "periods" in expression
            else 1
        )
        return self._within_groups(series, lambda part: part.diff(periods))

    def _as_count(self, expression: Any, context: str) -> int:
        value = expression if _is_integer(expression) else self.evaluate(expression)
        _require(
            _is_integer(value),
            f"{context.capitalize()} must be an integer.",
            code="malformed_expression",
        )
        return int(value)

    def _as_series(self, value: Any, context: str) -> pd.Series:
        _require(
            isinstance(value, pd.Series),
            f"Operator {context!r} requires an observation column, not a scalar.",
            code="malformed_expression",
        )
        return value

    def _within_groups(
        self, series: pd.Series, transform: Callable[[pd.Series], pd.Series]
    ) -> pd.Series:
        if self.group_keys is None:
            return transform(series)
        return series.groupby(self.group_keys, sort=False).transform(transform)

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
    _require(
        not missing,
        f"Unknown grouping columns: {missing}.",
        code="unknown_grouping_column",
        locus={"columns": missing},
    )
    return group_by


def _validation_row(check: str, passed: bool, details: str) -> dict[str, Any]:
    return {"check": check, "passed": passed, "details": details}


def _derive_columns(
    output: pd.DataFrame,
    contract: Mapping[str, Any],
    *,
    version: str,
    group_keys: Any,
) -> list[str]:
    """Add every declared derived column to ``output``, in declaration order.

    Missing values are expected here: a rolling window or a shift has nothing
    to say at the edges of a series. What the contract does about them is the
    job of ``missing_policy``, decided once the states are evaluated.
    """
    derive = contract.get("derive")
    if derive is None:
        return []
    _require(
        version == CONTRACT_V2,
        f"'derive' requires '{CONTRACT_V2}'.",
        code="operator_requires_v2",
        locus={"section": "derive"},
    )
    _require(
        isinstance(derive, Mapping) and bool(derive),
        "'derive' must be a non-empty mapping of column names to expressions.",
    )
    evaluator = _ExpressionEvaluator(
        output,
        contract.get("parameters", {}),
        "error",
        version=version,
        group_keys=group_keys,
        check_missing=False,
    )
    derived: list[str] = []
    for name, expression in derive.items():
        _require(
            isinstance(name, str) and bool(name),
            "Derived column names must be non-empty strings.",
        )
        _require(
            name not in output.columns,
            f"Derived column {name!r} already exists in the observations.",
            code="derived_column_collision",
            locus={"column": name},
        )
        _require(
            name not in RESERVED_COLUMNS and not name.startswith(RESERVED_PREFIX),
            f"Derived column {name!r} uses a name the compiler reserves.",
            code="derived_column_collision",
            locus={"column": name},
        )
        value = evaluator.evaluate(expression)
        _require(
            isinstance(value, pd.Series),
            f"Derived column {name!r} must evaluate to one value per observation.",
            code="malformed_expression",
            locus={"column": name},
        )
        output[name] = value
        derived.append(name)
    return derived


def _invalid_summary(valid: pd.Series, group_keys: Any) -> str:
    """Say where the excluded observations sit, so an exclusion stays visible.

    Leading and trailing gaps are what a window or a shift produces at the
    edges of every group. An interior gap is something else -- missing source
    data -- and under ``exclude`` it does not split an occurrence, so it is
    counted separately rather than folded into the edges.
    """
    invalid = ~valid
    if not invalid.any():
        return "excluded=0"
    leading = trailing = 0
    parts = (
        [valid]
        if group_keys is None
        else [part for _, part in valid.groupby(group_keys, sort=False)]
    )
    for part in parts:
        flags = part.to_numpy()
        if not flags.any():
            leading += len(flags)
            continue
        first = int(flags.argmax())
        last = len(flags) - 1 - int(flags[::-1].argmax())
        leading += first
        trailing += len(flags) - 1 - last
    total = int(invalid.sum())
    interior = total - leading - trailing
    return f"excluded={total} leading={leading} trailing={trailing} interior={interior}"


def _compile_partition(
    output: pd.DataFrame,
    contract: Mapping[str, Any],
    *,
    version: str,
    missing_policy: str,
    group_by: list[str],
    report: list[dict[str, Any]],
) -> pd.DataFrame:
    """Evaluate states, occurrences, and events over observations already valid."""
    group_keys = _group_keys(output, group_by)
    states = contract.get("states")
    state_column = contract.get("state_column")

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
            output,
            contract.get("parameters", {}),
            missing_policy,
            version=version,
            group_keys=group_keys,
        )
        masks: dict[str, pd.Series] = {}
        for name, expression in states.items():
            value = evaluator.evaluate(expression)
            masks[name] = evaluator._as_boolean(value, f"state {name!r}")
            output[f"state__{name}"] = masks[name]
        count = pd.concat(masks, axis=1).sum(axis=1)
        validation = contract.get("validation", {})
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
                f"States overlap at observation indices {_sample_indices(overlap)}.",
                code="states_overlap",
                locus={"observation_indices": _sample_indices(overlap)},
            )
        if exhaustive and gap.any():
            raise StateContractError(
                f"No state is active at observation indices {_sample_indices(gap)}.",
                code="states_not_exhaustive",
                locus={"observation_indices": _sample_indices(gap)},
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
        _require(
            state_column in output,
            f"Unknown state column: {state_column!r}.",
            code="unknown_state_column",
            locus={"column": state_column},
        )
        missing = output[state_column].isna()
        if missing.any():
            raise StateContractError(
                f"State column {state_column!r} contains missing values at "
                f"{_sample_indices(missing)}.",
                code="missing_values_in_input",
                locus={
                    "column": state_column,
                    "observation_indices": _sample_indices(missing),
                },
            )
        output["state"] = output[state_column]
        report.append(
            _validation_row("external_state_complete", True, f"column={state_column!r}")
        )
        declared_labels = None

    boundary = contract.get("boundary_policy", {})
    _require(isinstance(boundary, Mapping), "'boundary_policy' must be a mapping.")
    include_first = boundary.get("include_first_entry", True)
    include_last = boundary.get("include_last_exit", True)
    _require(isinstance(include_first, bool), "'include_first_entry' must be boolean.")
    _require(isinstance(include_last, bool), "'include_last_exit' must be boolean.")

    structural_entries = enter_label(output["state"], group_keys, include_first=True)
    if group_by:
        output["state_occurrence_id"] = (
            structural_entries.groupby(group_keys, sort=False).cumsum().astype("int64")
            - 1
        )
    else:
        output["state_occurrence_id"] = structural_entries.cumsum().astype("int64") - 1

    events = contract.get("events", {})
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
            event_type in {"enter_state", "exit_state", "enter_label", "exit_label"},
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
                    code="undeclared_state_in_event",
                    locus={"event": event_name, "state": label},
                )
            boundary_mask = entered if event_type == "enter_state" else exited
            output[event_name] = (boundary_mask & output["state"].eq(label)).astype(
                bool
            )

    occurrence_groups: Any = [*group_by, "state_occurrence_id"]
    constant = (
        output.groupby(occurrence_groups, dropna=False)["state"].nunique().le(1).all()
    )
    report.append(
        _validation_row(
            "occurrence_reconstruction",
            bool(constant),
            f"occurrences={output.groupby(occurrence_groups, dropna=False).ngroups}",
        )
    )
    _require(
        bool(constant),
        "Occurrence IDs do not reconstruct constant state runs.",
        code="occurrence_reconstruction_failed",
    )
    report.append(_validation_row("event_references", True, f"events={len(events)}"))
    return output


def _valid_observations(output: pd.DataFrame, contract: Mapping[str, Any]) -> pd.Series:
    """Rows on which every column the states read is present."""
    states = contract.get("states")
    if states is not None:
        _require(isinstance(states, Mapping), "'states' must be a non-empty mapping.")
        columns: set[str] = set()
        for expression in states.values():
            _referenced_columns(expression, columns)
        for column in sorted(columns):
            _require(
                column in output,
                f"Unknown input column: {column!r}.",
                code="unknown_column",
                locus={"column": column},
            )
        if not columns:
            return pd.Series(True, index=output.index)
        return ~output[sorted(columns)].isna().any(axis=1)
    state_column = contract.get("state_column")
    _require(isinstance(state_column, str), "'state_column' must be a string.")
    _require(
        state_column in output,
        f"Unknown state column: {state_column!r}.",
        code="unknown_state_column",
        locus={"column": state_column},
    )
    return output[state_column].notna()


def compile_states(
    observations: pd.DataFrame, contract: Mapping[str, Any]
) -> CompiledStateResult:
    """Compile a declarative contract without mutating the input observations.

    A contract supplies either named boolean ``states`` or an existing
    categorical ``state_column``. It may also declare enter and exit events.

    ``state-contract-v1`` reads observation columns as given: scientific
    preprocessing stays outside the compiler. ``state-contract-v2`` adds a
    ``derive`` section, so a construction such as a rolling envelope and its
    first difference can be declared in the contract and fingerprinted with
    it, and a ``missing_policy`` of ``"exclude"``, which leaves the observations
    a derivation cannot define outside the partition and reports them. Both
    versions compile through the same partition, occurrence and event rules.
    """
    _require(
        isinstance(observations, pd.DataFrame), "Observations must be a DataFrame."
    )
    _require(isinstance(contract, Mapping), "Contract must be a mapping.")
    frozen_contract = deepcopy(dict(contract))
    version = frozen_contract.get("version")
    _require(
        version in SUPPORTED_VERSIONS,
        f"Contract 'version' must be one of {list(SUPPORTED_VERSIONS)}.",
    )
    missing_policy = frozen_contract.get("missing_policy", "error")
    if version == CONTRACT_V1:
        _require(missing_policy == "error", "Only missing_policy='error' is supported.")
    else:
        _require(
            missing_policy in {"error", "exclude"},
            "missing_policy must be 'error' or 'exclude'.",
        )
    output = observations.copy(deep=True)
    group_by = _normalize_group_by(frozen_contract, output)

    states = frozen_contract.get("states")
    state_column = frozen_contract.get("state_column")
    _require(
        (states is None) != (state_column is None),
        "Declare exactly one of 'states' or 'state_column'.",
    )
    report: list[dict[str, Any]] = []

    derived = _derive_columns(
        output,
        frozen_contract,
        version=version,
        group_keys=_group_keys(output, group_by),
    )
    if derived:
        report.append(_validation_row("derived_columns", True, f"columns={derived}"))

    if missing_policy == "error":
        _compile_partition(
            output,
            frozen_contract,
            version=version,
            missing_policy=missing_policy,
            group_by=group_by,
            report=report,
        )
    else:
        valid = _valid_observations(output, frozen_contract)
        _require(
            bool(valid.any()),
            "Every observation is excluded; nothing remains to compile.",
            code="no_valid_observations",
        )
        working = _compile_partition(
            output.loc[valid].copy(),
            frozen_contract,
            version=version,
            missing_policy=missing_policy,
            group_by=group_by,
            report=report,
        )
        mask = valid.to_numpy()
        for column in working.columns:
            if column in output.columns:
                continue
            if column == "state":
                # None, not NaN: an excluded row has no label, and object
                # dtype keeps that distinct from a numeric hole.
                labels = np.full(len(output), None, dtype=object)
                labels[mask] = working[column].to_numpy(dtype=object)
                output[column] = pd.Series(labels, index=output.index, dtype=object)
            elif column == "state_occurrence_id":
                output[column] = pd.Series(pd.NA, index=output.index, dtype="Int64")
                output.loc[valid, column] = working[column]
            else:
                output[column] = False
                output.loc[valid, column] = working[column]
        output["state_valid"] = valid.astype(bool)
        report.append(
            _validation_row(
                "invalid_observations",
                True,
                _invalid_summary(valid, _group_keys(output, group_by)),
            )
        )

    return CompiledStateResult(
        observations=output,
        validation_report=pd.DataFrame(report),
        contract=frozen_contract,
    )
