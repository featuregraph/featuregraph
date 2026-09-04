"""Render an intake as the prose a researcher might have written, and ablate it.

The completeness eval needs briefs a model reads and turns back into an
intake. A brief is rendered from a reference intake so that its content is
known exactly, and it is rendered as prose and plain bullet lines rather
than as the intake's JSON, so that producing a compilable intake requires
the model to give the answers structure, not copy it.

Two ablations produce cases with a known correct answer:

- withholding one field: the brief omits that section, so the field ought
  to come back unset and the model ought to say so;
- flattening a compilable field: its rule is rendered as one sentence with
  no notation, so a model that transcribes it produces prose the compiler
  cannot execute, and ought to say so.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from featuregraph.study_builder.intake import (
    COMPILABLE,
    FIELDS,
    FIELDS_BY_NAME,
    StudyIntake,
    StudyIntakeError,
    _describe_expression,
)


@dataclass(frozen=True)
class BriefCase:
    """One brief and what was done to it."""

    case_id: str
    reference: str
    text: str
    withheld: tuple[str, ...] = ()
    flattened: tuple[str, ...] = ()


def _lines(value: Any, *, flatten: bool = False) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        if "state_column" in value and len(value) == 1:
            column = value["state_column"]
            return [f"The states are already supplied in the column {column}."]
        out = []
        for key in value:
            item = value[key]
            if isinstance(item, Mapping | list):
                out.append(f"- {key}: {_inline(item)}")
            else:
                out.append(f"- {key}: {item}")
        return out
    if isinstance(value, list):
        if not value:
            return ["None; there are none."]
        out = []
        for entry in value:
            if isinstance(entry, Mapping) and {"name", "when"} <= set(entry):
                rule = (
                    _prose_rule(entry["when"])
                    if flatten
                    else _describe_expression(entry["when"])
                )
                out.append(f"- {entry['name']}: when {rule}")
            elif isinstance(entry, Mapping):
                out.append("- " + ", ".join(f"{k} {v}" for k, v in entry.items()))
            else:
                out.append(f"- {entry}")
        return out
    return [str(value)]


def _inline(value: Any) -> str:
    if isinstance(value, Mapping):
        return ", ".join(f"{k} {_inline(v)}" for k, v in value.items())
    if isinstance(value, list):
        return "; ".join(_inline(v) for v in value)
    return str(value)


_WORDS = {
    "gt": "is greater than",
    "ge": "is at least",
    "lt": "is less than",
    "le": "is at most",
    "eq": "equals",
    "ne": "differs from",
}


def _prose_rule(expression: Any) -> str:
    """One sentence, no operator notation, for the flattening ablation."""
    if not isinstance(expression, Mapping):
        return str(expression)
    if "column" in expression:
        return f"the {expression['column']} value"
    if "parameter" in expression:
        return f"the {expression['parameter']} threshold"
    op = expression.get("op")
    if op in _WORDS:
        left = _prose_rule(expression.get("left"))
        right = _prose_rule(expression.get("right"))
        return f"{left} {_WORDS[op]} {right}"
    if op == "neg":
        return f"minus {_prose_rule(expression.get('value'))}"
    if op == "abs":
        return f"the size of {_prose_rule(expression.get('value'))}"
    if op in {"and", "or"}:
        parts = [_prose_rule(v) for v in expression.get("values", [])]
        return f" {op} ".join(parts)
    return _describe_expression(expression)


def render_brief(
    intake: StudyIntake,
    *,
    withhold: Sequence[str] = (),
    flatten: Sequence[str] = (),
) -> str:
    """The reference intake as a researcher's brief.

    Every declared field becomes a short section under the field's heading,
    in the order the intake lists its fields. Withheld fields are left out
    entirely, without a placeholder, because a placeholder would tell the
    model what is missing.
    """
    for name in (*withhold, *flatten):
        if name not in FIELDS_BY_NAME:
            raise StudyIntakeError(f"Unknown intake field: {name!r}.")
    lines = [
        "A researcher describes the study they want to run. Read the whole "
        "brief; it is everything they have said.",
        "",
    ]
    for field in FIELDS:
        if field.name in withhold:
            continue
        value = intake.get(field.name)
        if value is None:
            continue
        lines += [f"## {field.heading}", ""]
        lines += _lines(value, flatten=field.name in flatten)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def ablations(reference: str, intake: StudyIntake) -> Iterator[BriefCase]:
    """The full brief, one brief per withheld field, one per flattened rule."""
    yield BriefCase(f"{reference}/full", reference, render_brief(intake))
    for field in FIELDS:
        if intake.get(field.name) is None:
            continue
        yield BriefCase(
            f"{reference}/withhold/{field.name}",
            reference,
            render_brief(intake, withhold=(field.name,)),
            withheld=(field.name,),
        )
    for field in FIELDS:
        value = intake.get(field.name)
        if field.tier != COMPILABLE or not isinstance(value, list):
            continue
        if not any(isinstance(e, Mapping) and "when" in e for e in value):
            continue
        yield BriefCase(
            f"{reference}/flatten/{field.name}",
            reference,
            render_brief(intake, flatten=(field.name,)),
            flattened=(field.name,),
        )
