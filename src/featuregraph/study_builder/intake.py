"""Represent a study intake as a contract that still has holes in it.

The conversational Study Builder used to carry two unrelated objects: an intake
JSON a model filled in turn by turn, and a compiler contract someone wrote by
hand afterwards. Nothing checked that the second followed from the first, and
the intake's own ``missing_information`` list was maintained by the same model
that was filling the fields in -- so the record of what was still unknown was
only as trustworthy as the thing being audited.

This module collapses the two. A :class:`StudyIntake` *is* a study contract
whose fields may be unset. ``missing_information`` is derived from which ones
still are; it is never stored and never asserted by a model. Once enough is
declared, the same object emits a real ``state-contract-v1`` mapping for
:func:`featuregraph.contracts.compile_states` and an approval-free candidate
for :func:`featuregraph.contracts.approve_study_contract`.

Two tiers of completeness are tracked separately, because they answer different
questions and the flat v1 list conflated them:

``compilable``
    What the compiler needs before a contract can be emitted at all.
``approvable``
    What a researcher should have declared before putting their name to it.

A study can be compilable and not approvable. The reverse is also possible, and
both are useful things to be able to say.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any

INTAKE_SCHEMA_VERSION = 2
STATE_CONTRACT_VERSION = "state-contract-v1"
STUDY_CONTRACT_VERSION = "study-contract-v1"

COMPILABLE = "compilable"
APPROVABLE = "approvable"

#: What v1 wrote into a text field it had not yet filled in.
V1_TEXT_SENTINEL = "Not yet specified"


class StudyIntakeError(ValueError):
    """Raised when an intake is malformed or asked for more than it holds."""


class IntakeIncompleteError(StudyIntakeError):
    """Raised when an intake cannot yet produce what was asked of it.

    Carries the two reasons separately: fields nobody has answered, and fields
    answered in prose where the compiler needs structure. Telling a researcher
    "you never said" and "you said it, but not in a form I can execute" are
    different conversations.
    """

    def __init__(
        self,
        message: str,
        *,
        unset: Sequence[str] = (),
        unstructured: Sequence[str] = (),
    ) -> None:
        super().__init__(message)
        self.unset = tuple(unset)
        self.unstructured = tuple(unstructured)


@dataclass(frozen=True)
class IntakeField:
    """One declarable field, and what it is being asked for."""

    name: str
    tier: str
    kind: str  # "text" or "list"
    heading: str
    prompt: str

    def is_unset(self, value: Any) -> bool:
        """Whether ``value`` counts as nobody having answered.

        ``None`` alone means unset. An empty list is a real answer -- "there is
        no preprocessing", "no rows are excluded" -- and v1 could not say that,
        because it used ``[]`` for both.
        """
        return value is None


FIELDS: tuple[IntakeField, ...] = (
    IntakeField(
        "title",
        APPROVABLE,
        "text",
        "Title",
        "A short name for this study.",
    ),
    IntakeField(
        "research_question",
        APPROVABLE,
        "text",
        "Research question",
        "The question this study answers, stated so a negative result is recognisable.",
    ),
    IntakeField(
        "data_source",
        APPROVABLE,
        "text",
        "Data source",
        "Where the observations come from, specifically enough to fetch them again.",
    ),
    IntakeField(
        "observation_schema",
        COMPILABLE,
        "list",
        "Observation schema",
        "One entry per input column: its name, dtype, and unit.",
    ),
    IntakeField(
        "grouping_and_order",
        COMPILABLE,
        "list",
        "Grouping and order",
        "Which columns separate independent series, and which column orders "
        "rows within one.",
    ),
    IntakeField(
        "time_semantics",
        APPROVABLE,
        "text",
        "Time semantics",
        "What one row's timestamp means: an instant, or an interval that ends there.",
    ),
    IntakeField(
        "states_or_labels",
        COMPILABLE,
        "list",
        "States or supplied labels",
        "Either the boolean rule for each state, or the column that already "
        "holds labels.",
    ),
    IntakeField(
        "preprocessing_steps",
        APPROVABLE,
        "list",
        "Preprocessing steps",
        "Anything done to the observations before the compiler sees them.",
    ),
    IntakeField(
        "operator_parameters",
        COMPILABLE,
        "list",
        "Operator parameters",
        "Named thresholds the state rules refer to, with their values.",
    ),
    IntakeField(
        "boundary_rules",
        COMPILABLE,
        "list",
        "Boundary rules",
        "Whether a series' first entry and last exit count as events.",
    ),
    IntakeField(
        "completeness_rules",
        COMPILABLE,
        "list",
        "Completeness rules",
        "Whether states must be mutually exclusive, and whether they must "
        "cover every row.",
    ),
    IntakeField(
        "object_definition",
        APPROVABLE,
        "text",
        "Object definition",
        "What one row of the result stands for.",
    ),
    IntakeField(
        "measurements",
        APPROVABLE,
        "list",
        "Measurements",
        "The statistics computed over those objects.",
    ),
    IntakeField(
        "validations",
        APPROVABLE,
        "list",
        "Validations",
        "Checks that must pass before the result is believed.",
    ),
    IntakeField(
        "provenance",
        APPROVABLE,
        "list",
        "Provenance to retain",
        "What is recorded about how this study was produced.",
    ),
    IntakeField(
        "exclusions",
        APPROVABLE,
        "list",
        "Exclusions",
        "Rows or series left out, and on what rule.",
    ),
    IntakeField(
        "claim_limits",
        APPROVABLE,
        "list",
        "Claim limits",
        "What this study does not establish.",
    ),
)

FIELDS_BY_NAME: dict[str, IntakeField] = {field.name: field for field in FIELDS}

_RESERVED_KEYS = frozenset(
    {"schema_version", "status", "executor_registered", "missing_information"}
)


def _text(value: Any, field: IntakeField) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StudyIntakeError(
            f"Field {field.name!r} takes a non-empty string, or None to leave "
            "it unanswered."
        )
    return value.strip()


def _listing(value: Any, field: IntakeField) -> list[Any]:
    if isinstance(value, Mapping):
        return deepcopy(dict(value))  # type: ignore[return-value]
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise StudyIntakeError(
            f"Field {field.name!r} takes a list or mapping, or None to leave "
            "it unanswered."
        )
    return deepcopy(list(value))


def _normalize(name: str, value: Any) -> Any:
    field = FIELDS_BY_NAME.get(name)
    if field is None:
        raise StudyIntakeError(f"Unknown intake field: {name!r}.")
    if value is None:
        return None
    if field.kind == "text":
        return _text(value, field)
    return _listing(value, field)


class _ShapeError(StudyIntakeError):
    """Internal: a declared field is prose where structure is required."""


def _columns(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise _ShapeError("observation_schema must be a list of column entries.")
    entries: list[dict[str, Any]] = []
    for entry in value:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("column"), str):
            raise _ShapeError("Every observation_schema entry needs a 'column' name.")
        entries.append(dict(entry))
    return entries


def _grouping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise _ShapeError(
            "grouping_and_order must be a mapping with 'group_by' and 'order_by'."
        )
    raw = value.get("group_by", [])
    group_by = [raw] if isinstance(raw, str) else list(raw or [])
    if not all(isinstance(column, str) for column in group_by):
        raise _ShapeError("Every 'group_by' entry must be a column name.")
    order_by = value.get("order_by")
    if not isinstance(order_by, str) or not order_by:
        raise _ShapeError("grouping_and_order must name an 'order_by' column.")
    return {"group_by": group_by, "order_by": order_by}


def _states(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        column = value.get("state_column")
        if not isinstance(column, str) or not column:
            raise _ShapeError(
                "states_or_labels as a mapping must name a 'state_column'."
            )
        return {"state_column": column}
    if not isinstance(value, list) or not value:
        raise _ShapeError(
            "states_or_labels must be a non-empty list of {'name', 'when'} "
            "entries, or a mapping naming a 'state_column'."
        )
    states: dict[str, Any] = {}
    for entry in value:
        if not isinstance(entry, Mapping):
            raise _ShapeError("Every state entry must be a mapping.")
        name = entry.get("name")
        when = entry.get("when")
        if not isinstance(name, str) or not name:
            raise _ShapeError("Every state entry needs a non-empty 'name'.")
        if not isinstance(when, Mapping):
            raise _ShapeError(f"State {name!r} needs a 'when' expression, not prose.")
        if name in states:
            raise _ShapeError(f"State {name!r} is declared twice.")
        states[name] = deepcopy(dict(when))
    return {"states": states}


def _parameters(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {"parameters": deepcopy(dict(value))}
    if not isinstance(value, list):
        raise _ShapeError("operator_parameters must be a list or a mapping.")
    parameters: dict[str, Any] = {}
    for entry in value:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("name"), str):
            raise _ShapeError(
                "Every operator_parameters entry needs a 'name' and a 'value'."
            )
        if "value" not in entry:
            raise _ShapeError(
                f"Parameter {entry['name']!r} is named but has no 'value'."
            )
        parameters[entry["name"]] = deepcopy(entry["value"])
    return {"parameters": parameters}


def _flags(value: Any, allowed: Mapping[str, str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise _ShapeError(
            f"{label} must be a mapping of {sorted(allowed)} to booleans."
        )
    unknown = sorted(set(value) - set(allowed))
    if unknown:
        raise _ShapeError(f"{label} does not accept {unknown}.")
    resolved: dict[str, Any] = {}
    for key, target in allowed.items():
        if key not in value:
            raise _ShapeError(f"{label} must state {key!r}.")
        if not isinstance(value[key], bool):
            raise _ShapeError(f"{label}[{key!r}] must be true or false.")
        resolved[target] = value[key]
    return resolved


def _boundary(value: Any) -> dict[str, Any]:
    policy = _flags(
        value,
        {
            "include_first_entry": "include_first_entry",
            "include_last_exit": "include_last_exit",
        },
        "boundary_rules",
    )
    return {"boundary_policy": policy}


def _completeness(value: Any) -> dict[str, Any]:
    validation = _flags(
        value,
        {"exclusive": "exclusive", "exhaustive": "exhaustive"},
        "completeness_rules",
    )
    return {"validation": validation}


#: How each compilable field turns into a fragment of a ``state-contract-v1``.
_COMPILERS = {
    "observation_schema": lambda value: {"_columns": _columns(value)},
    "grouping_and_order": _grouping,
    "states_or_labels": _states,
    "operator_parameters": _parameters,
    "boundary_rules": _boundary,
    "completeness_rules": _completeness,
}


def _references(expression: Any, columns: set[str], parameters: set[str]) -> None:
    """Walk a state expression and collect its column and parameter names."""
    if isinstance(expression, Mapping):
        if set(expression) == {"column"} and isinstance(expression["column"], str):
            columns.add(expression["column"])
            return
        if set(expression) == {"parameter"} and isinstance(
            expression["parameter"], str
        ):
            parameters.add(expression["parameter"])
            return
        for value in expression.values():
            _references(value, columns, parameters)
        return
    if isinstance(expression, list):
        for value in expression:
            _references(value, columns, parameters)


@dataclass(frozen=True)
class StudyIntake:
    """A study contract whose fields may not be declared yet.

    Immutable. :meth:`declare` returns a new intake rather than mutating this
    one, so a conversation's history is a list of intakes and any turn can be
    replayed or discarded without unwinding shared state.
    """

    values: Mapping[str, Any]
    executor_registered: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.values, Mapping):
            raise StudyIntakeError("An intake's values must be a mapping.")
        unknown = sorted(set(self.values) - set(FIELDS_BY_NAME))
        if unknown:
            raise StudyIntakeError(f"Unknown intake fields: {unknown}.")
        object.__setattr__(
            self,
            "values",
            {
                name: _normalize(name, self.values[name])
                for name in FIELDS_BY_NAME
                if name in self.values
            },
        )

    # -- construction ----------------------------------------------------

    @classmethod
    def empty(cls) -> StudyIntake:
        """An intake with nothing declared."""
        return cls(values={})

    def declare(self, **fields: Any) -> StudyIntake:
        """Return a new intake with ``fields`` set.

        Passing ``None`` retracts a field, which is how a researcher takes back
        something a model filled in on their behalf.
        """
        merged = dict(self.values)
        for name, value in fields.items():
            if name not in FIELDS_BY_NAME:
                raise StudyIntakeError(f"Unknown intake field: {name!r}.")
            if value is None:
                merged.pop(name, None)
            else:
                merged[name] = value
        return replace(self, values=merged)

    def get(self, name: str) -> Any:
        """The declared value of ``name``, or ``None`` if it is unset."""
        if name not in FIELDS_BY_NAME:
            raise StudyIntakeError(f"Unknown intake field: {name!r}.")
        return deepcopy(self.values.get(name))

    # -- derived completeness --------------------------------------------

    @property
    def missing_information(self) -> tuple[str, ...]:
        """Every field nobody has answered, derived and never stored.

        v1 kept this list in the payload, written by the same model that filled
        the fields in. Deriving it means the record of what is unknown cannot
        disagree with what is actually there.
        """
        return tuple(
            field.name
            for field in sorted(FIELDS, key=lambda item: item.name)
            if field.name not in self.values
        )

    def missing_in_tier(self, tier: str) -> tuple[str, ...]:
        """The unanswered fields belonging to one completeness tier."""
        if tier not in (COMPILABLE, APPROVABLE):
            raise StudyIntakeError(f"Unknown completeness tier: {tier!r}.")
        return tuple(
            name
            for name in self.missing_information
            if FIELDS_BY_NAME[name].tier == tier
        )

    @property
    def unstructured(self) -> tuple[str, ...]:
        """Compilable fields that were answered, but not in a compilable shape.

        This is the state v1 could not express: the researcher has said
        something, so it is not missing, but it is prose where the compiler
        needs a rule.
        """
        names: list[str] = []
        for name, compile_fragment in _COMPILERS.items():
            if name not in self.values:
                continue
            try:
                compile_fragment(self.values[name])
            except _ShapeError:
                names.append(name)
        return tuple(sorted(names))

    @property
    def is_compilable(self) -> bool:
        """Whether :meth:`to_state_contract` would succeed."""
        try:
            self.to_state_contract()
        except IntakeIncompleteError:
            return False
        return True

    @property
    def is_approvable(self) -> bool:
        """Whether every field is answered and the compilable ones are shaped."""
        return not self.missing_information and not self.unstructured

    @property
    def status(self) -> str:
        """Where this intake sits, stated the way v1's ``status`` field did."""
        if self.is_approvable:
            return "awaiting_approval"
        return "intake_in_progress"

    # -- emission --------------------------------------------------------

    def to_state_contract(self) -> dict[str, Any]:
        """Emit a ``state-contract-v1`` mapping ``compile_states`` accepts.

        Raises :class:`IntakeIncompleteError` naming exactly what is missing and
        what is prose, so a caller never has to guess which of the two it is.
        """
        unset = self.missing_in_tier(COMPILABLE)
        unstructured = self.unstructured
        if unset or unstructured:
            parts = []
            if unset:
                parts.append(f"not yet declared: {', '.join(unset)}")
            if unstructured:
                parts.append(f"declared without structure: {', '.join(unstructured)}")
            raise IntakeIncompleteError(
                "This intake cannot compile yet -- " + "; ".join(parts) + ".",
                unset=unset,
                unstructured=unstructured,
            )

        fragments: dict[str, Any] = {}
        for name, compile_fragment in _COMPILERS.items():
            fragments.update(compile_fragment(self.values[name]))

        declared_columns = {entry["column"] for entry in fragments.pop("_columns")}
        grouping = {
            "group_by": fragments.pop("group_by"),
            "order_by": fragments.pop("order_by"),
        }

        contract: dict[str, Any] = {
            "version": STATE_CONTRACT_VERSION,
            "missing_policy": "error",
            "group_by": grouping["group_by"],
        }
        contract.update(fragments)

        self._check_references(contract, declared_columns, grouping)
        return contract

    def _check_references(
        self,
        contract: Mapping[str, Any],
        declared_columns: set[str],
        grouping: Mapping[str, Any],
    ) -> None:
        """Refuse a contract that names columns the intake never declared.

        The compiler raises ``unknown_column`` for this too, but only once the
        data is loaded. Catching it here means a researcher hears about a typo
        during intake rather than after a dataset fetch.
        """
        used_columns: set[str] = set(grouping["group_by"]) | {grouping["order_by"]}
        used_parameters: set[str] = set()
        if "state_column" in contract:
            used_columns.add(contract["state_column"])
        else:
            _references(contract["states"], used_columns, used_parameters)

        unknown = sorted(used_columns - declared_columns)
        if unknown:
            raise IntakeIncompleteError(
                "These columns are used but absent from the observation "
                f"schema: {', '.join(unknown)}.",
                unstructured=("observation_schema",),
            )
        undeclared = sorted(used_parameters - set(contract.get("parameters", {})))
        if undeclared:
            raise IntakeIncompleteError(
                "These parameters are used but never given a value: "
                f"{', '.join(undeclared)}.",
                unstructured=("operator_parameters",),
            )

    def to_study_candidate(self) -> dict[str, Any]:
        """Emit an approval-free candidate for ``approve_study_contract``.

        Every hole in the intake becomes an entry in ``unresolved_questions``,
        which is the field the existing approval gate already refuses on. No new
        enforcement is added here: an incomplete intake is simply unapprovable
        by the rule that was already there.
        """
        candidate: dict[str, Any] = {
            "contract_version": STUDY_CONTRACT_VERSION,
            "intake_schema_version": INTAKE_SCHEMA_VERSION,
            "executor_registered": self.executor_registered,
        }
        for field in FIELDS:
            if field.name in self.values:
                candidate[field.name] = deepcopy(self.values[field.name])

        unresolved = [
            f"{name}: {FIELDS_BY_NAME[name].prompt}"
            for name in self.missing_information
        ]
        unresolved += [
            f"{name}: declared, but not in a form the compiler can execute."
            for name in self.unstructured
        ]
        try:
            candidate["state_contract"] = self.to_state_contract()
        except IntakeIncompleteError as error:
            if not unresolved:  # pragma: no cover - defensive
                unresolved.append(str(error))
        candidate["unresolved_questions"] = unresolved
        return candidate

    # -- serialisation ---------------------------------------------------

    def to_payload(self) -> dict[str, Any]:
        """A JSON-serialisable intake, with ``missing_information`` derived."""
        payload: dict[str, Any] = {
            "schema_version": INTAKE_SCHEMA_VERSION,
            "status": self.status,
            "executor_registered": self.executor_registered,
        }
        for field in FIELDS:
            payload[field.name] = deepcopy(self.values.get(field.name))
        payload["missing_information"] = list(self.missing_information)
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> StudyIntake:
        """Load an intake payload, reading v1 the way v1 meant it.

        v1 had no way to distinguish "unanswered" from "answered as nothing":
        it wrote ``"Not yet specified"`` into unanswered text fields and ``[]``
        into unanswered lists. Both are read here as unset, so an existing
        checkpoint round-trips. From v2 on, only ``None`` means unset, and an
        empty list is a researcher saying there are none.
        """
        if not isinstance(payload, Mapping):
            raise StudyIntakeError("An intake payload must be a mapping.")
        version = payload.get("schema_version", INTAKE_SCHEMA_VERSION)
        if version not in (1, INTAKE_SCHEMA_VERSION):
            raise StudyIntakeError(f"Unsupported intake schema_version: {version!r}.")
        unknown = sorted(set(payload) - set(FIELDS_BY_NAME) - _RESERVED_KEYS)
        if unknown:
            raise StudyIntakeError(f"Unknown intake fields: {unknown}.")

        values: dict[str, Any] = {}
        for field in FIELDS:
            if field.name not in payload:
                continue
            value = payload[field.name]
            if value is None:
                continue
            if version == 1 and (value == V1_TEXT_SENTINEL or value == []):
                continue
            values[field.name] = value
        return cls(
            values=values,
            executor_registered=bool(payload.get("executor_registered", False)),
        )


_EXECUTION_BOUNDARY = (
    "This packet does not execute generated code. A deterministic data "
    "adapter, compiler contract, frozen fixture, and parity tests must be "
    "registered before this study can run."
)

_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Research question", ("research_question",)),
    (
        "Data and observations",
        ("data_source", "grouping_and_order", "time_semantics", "observation_schema"),
    ),
    (
        "Proposed representation",
        (
            "object_definition",
            "states_or_labels",
            "preprocessing_steps",
            "operator_parameters",
            "boundary_rules",
            "completeness_rules",
            "measurements",
        ),
    ),
    (
        "Validation and provenance",
        ("validations", "provenance", "exclusions", "claim_limits"),
    ),
)


def _render_value(field: IntakeField, value: Any) -> list[str]:
    if value is None:
        return [f"- {field.heading}: not yet specified"]
    if field.kind == "text":
        return [f"- {field.heading}: {value}"]
    if isinstance(value, Mapping):
        if not value:
            return [f"- {field.heading}: declared as none"]
        return [f"- {field.heading}:"] + [
            f"  - {key}: {value[key]}" for key in sorted(value)
        ]
    if not value:
        return [f"- {field.heading}: declared as none"]
    return [f"- {field.heading}:"] + [f"  - {entry}" for entry in value]


def render_checkpoint(intake: StudyIntake, *, level: int = 1) -> str:
    """Render an intake as the markdown checkpoint, derived from the intake.

    The deployed v1 assistant wrote this text itself, which meant the summary a
    researcher read and the payload the compiler would receive were two
    separate model outputs that could disagree. Rendering it here makes the
    text a view of the data rather than a second claim about it.

    ``level`` shifts every heading down, so the same renderer can stand alone
    or sit inside a larger checkpoint without two copies of it existing.
    """
    if level < 1:
        raise StudyIntakeError("Heading level must be 1 or greater.")
    top = "#" * level
    sub = "#" * (level + 1)
    title = intake.get("title") or "Untitled study"
    lines = [
        f"{top} {title}: intake checkpoint v{INTAKE_SCHEMA_VERSION}",
        "",
        f"Status: **{intake.status.replace('_', ' ')}**",
    ]
    for heading, names in _SECTIONS:
        lines += ["", f"{sub} {heading}"]
        for name in names:
            lines += _render_value(FIELDS_BY_NAME[name], intake.get(name))

    lines += ["", f"{sub} Completeness"]
    for tier in (COMPILABLE, APPROVABLE):
        outstanding = intake.missing_in_tier(tier)
        detail = ", ".join(outstanding) if outstanding else "complete"
        lines.append(f"- Not yet declared ({tier}): {detail}")
    unstructured = intake.unstructured
    if unstructured:
        lines.append(f"- Declared without structure: {', '.join(unstructured)}")

    lines += [
        "",
        f"{sub} Execution boundary",
        "",
        f"- Executor registered: {'yes' if intake.executor_registered else 'no'}",
        f"- Compiles today: {'yes' if intake.is_compilable else 'no'}",
        f"- Approvable today: {'yes' if intake.is_approvable else 'no'}",
        "",
        _EXECUTION_BOUNDARY,
    ]
    return "\n".join(lines) + "\n"


def _dataset_reference(dataset: Mapping[str, Any]) -> str | None:
    parts = [
        str(dataset[key])
        for key in ("name", "version", "doi", "source_url")
        if isinstance(dataset.get(key), str) and dataset[key]
    ]
    return ", ".join(parts) or None


def _states_from_compiler(compiler: Mapping[str, Any]) -> Any:
    column = compiler.get("state_column")
    if isinstance(column, str) and column:
        return {"state_column": column}
    states = compiler.get("states")
    if isinstance(states, Mapping) and states:
        return [{"name": name, "when": rule} for name, rule in states.items()]
    return None


def _grouping_from_compiler(compiler: Mapping[str, Any]) -> Any:
    group_by = compiler.get("group_by")
    order_by = compiler.get("order_by")
    if group_by is None and order_by is None:
        return None
    # Deliberately partial. A state contract does not have to name an ordering
    # column -- the caller's adapter often supplies the order -- so this reads
    # back what is there and leaves the field to fail its shape check if the
    # ordering was never written down.
    return {"group_by": group_by if group_by is not None else [], "order_by": order_by}


def _provenance_from_contract(contract: Mapping[str, Any]) -> Any:
    approval = contract.get("approval")
    if not isinstance(approval, Mapping):
        return None
    return {
        key: approval[key]
        for key in ("authority", "status", "contract_sha256")
        if key in approval
    }


def intake_from_study_contract(contract: Mapping[str, Any]) -> StudyIntake:
    """Read an existing study contract back into an intake.

    This is the bridge for a study that already exists: a published contract
    becomes the starting point of a conversation about changing it, and the
    fields it never wrote down show up as open questions rather than as
    assumptions someone has to remember.

    Only conventions the contracts in this repository actually use are read.
    Anything a contract does not carry -- a research question, the observation
    schema, what preprocessing ran -- is left unset. Guessing here would put
    words in a researcher's mouth and then present them as declared.
    """
    if not isinstance(contract, Mapping):
        raise StudyIntakeError("A study contract must be a mapping.")

    study = contract.get("study") if isinstance(contract.get("study"), Mapping) else {}
    dataset = (
        contract.get("dataset") if isinstance(contract.get("dataset"), Mapping) else {}
    )
    compiler = (
        contract.get("state_compiler")
        if isinstance(contract.get("state_compiler"), Mapping)
        else {}
    )
    measurements = (
        contract.get("measurements")
        if isinstance(contract.get("measurements"), Mapping)
        else {}
    )

    declared: dict[str, Any] = {
        "title": study.get("name"),
        "object_definition": study.get("unit_of_analysis"),
        "data_source": _dataset_reference(dataset),
        "measurements": measurements.get("statistics"),
        "validations": contract.get("validations"),
        "exclusions": contract.get("exclusions"),
        "claim_limits": contract.get("claim_boundaries"),
        "provenance": _provenance_from_contract(contract),
        "states_or_labels": _states_from_compiler(compiler),
        "grouping_and_order": _grouping_from_compiler(compiler),
        "operator_parameters": compiler.get("parameters"),
        "boundary_rules": compiler.get("boundary_policy"),
        "completeness_rules": compiler.get("validation"),
    }
    return StudyIntake.empty().declare(
        **{name: value for name, value in declared.items() if value is not None}
    )
