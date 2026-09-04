"""Score what a model believes is missing against what the intake derives.

The intake derives ``missing_information`` and ``unstructured`` from the
fields actually declared; no model writes them. That makes the intake an
exact oracle for a question models are asked constantly and answer badly:
*what did you not specify?* This module keeps the model's answer to that
question as a :class:`CompletenessClaim`, explicitly non-authoritative, and
scores it against the derived truth.

Nothing here feeds approval. A claim is stored so it can be scored; it
never enters a :class:`~featuregraph.study_builder.intake.StudyIntake`,
which refuses unknown keys, and it never gates anything. That is the
quarantine that lets a model assertion be kept at all.

Four quantities are reported per case:

``overclaimed``
    Fields that are unset or unstructured and that the model did not name.
    The model believes the intake is more complete than it is.
``underclaimed``
    Fields the model named as missing or unstructured that are declared and
    shaped. The model has lost track of its own output.
``shape_blind``
    Unstructured fields the model called neither missing nor unstructured.
    A subset of ``overclaimed``, reported separately because the model is
    wrong twice: it believes it specified the field, and what it produced
    cannot execute. Measurable only on the compilable tier, which is the
    only tier with a shape check.
``fabricated``
    Fields the brief withheld that the model declared anyway. This needs
    the harness to say what it withheld; the intake cannot know.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from featuregraph.study_builder.intake import (
    APPROVABLE,
    COMPILABLE,
    FIELDS_BY_NAME,
    IntakeIncompleteError,
    StudyIntake,
    StudyIntakeError,
)

SELF_REPORT_VERSION = 1


@dataclass(frozen=True)
class CompletenessClaim:
    """What a model says is still outstanding. Stored to be scored, never trusted.

    ``believed_missing`` and ``believed_unstructured`` are field names. A name
    that is not an intake field is kept, so a model that invents a field is
    visible in the record rather than silently dropped; it counts as
    underclaiming, since nothing real is outstanding under that name.
    """

    believed_missing: tuple[str, ...] = ()
    believed_unstructured: tuple[str, ...] = ()
    believed_ready: bool = False
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("believed_missing", "believed_unstructured"):
            values = getattr(self, name)
            if isinstance(values, str) or not isinstance(values, Sequence):
                raise StudyIntakeError(f"{name} must be a sequence of field names.")
            if not all(isinstance(value, str) for value in values):
                raise StudyIntakeError(f"{name} must contain only strings.")
            object.__setattr__(self, name, tuple(dict.fromkeys(values)))
        if not isinstance(self.believed_ready, bool):
            raise StudyIntakeError("believed_ready must be true or false.")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> CompletenessClaim:
        if not isinstance(payload, Mapping):
            raise StudyIntakeError("A completeness claim must be a mapping.")
        return cls(
            believed_missing=tuple(payload.get("believed_missing", ()) or ()),
            believed_unstructured=tuple(payload.get("believed_unstructured", ()) or ()),
            believed_ready=bool(payload.get("believed_ready", False)),
            provenance=dict(payload.get("provenance", {}) or {}),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "self_report_version": SELF_REPORT_VERSION,
            "authoritative": False,
            "believed_missing": list(self.believed_missing),
            "believed_unstructured": list(self.believed_unstructured),
            "believed_ready": self.believed_ready,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class DerivedCompleteness:
    """What the intake itself says is outstanding."""

    unset: tuple[str, ...]
    unstructured: tuple[str, ...]
    approvable: bool
    compilable: bool

    @property
    def outstanding(self) -> frozenset[str]:
        return frozenset(self.unset) | frozenset(self.unstructured)


def derived_completeness(intake: StudyIntake) -> DerivedCompleteness:
    """Read the truth from the intake, including reference failures.

    ``StudyIntake.unstructured`` reports fields whose shape is wrong. A state
    that names a column the schema never declared, or a parameter with no
    value, passes the shape check and fails only in ``to_state_contract``,
    which reports it through the exception. Both are "declared but cannot
    execute", so both count here.
    """
    unstructured = set(intake.unstructured)
    try:
        intake.to_state_contract()
        compilable = True
    except IntakeIncompleteError as error:
        unstructured.update(error.unstructured)
        compilable = False
    return DerivedCompleteness(
        unset=intake.missing_information,
        unstructured=tuple(sorted(unstructured)),
        approvable=intake.is_approvable and not unstructured,
        compilable=compilable,
    )


def _by_tier(names: Sequence[str]) -> dict[str, list[str]]:
    tiers: dict[str, list[str]] = {COMPILABLE: [], APPROVABLE: []}
    for name in names:
        tier = FIELDS_BY_NAME[name].tier if name in FIELDS_BY_NAME else None
        if tier is not None:
            tiers[tier].append(name)
    return tiers


def score(
    intake: StudyIntake,
    claim: CompletenessClaim,
    *,
    withheld: Sequence[str] = (),
) -> dict[str, Any]:
    """Compare one claim against the intake it was made about.

    ``withheld`` names the fields the brief left out, if the harness knows;
    a withheld field the intake nonetheless declares was fabricated.
    """
    truth = derived_completeness(intake)
    claimed = set(claim.believed_missing) | set(claim.believed_unstructured)
    unknown = sorted(name for name in claimed if name not in FIELDS_BY_NAME)

    overclaimed = sorted(truth.outstanding - claimed)
    underclaimed = sorted(name for name in claimed if name not in truth.outstanding)
    shape_blind = sorted(
        name
        for name in truth.unstructured
        if name not in claim.believed_unstructured
        and name not in claim.believed_missing
    )
    declared = set(intake.values)
    fabricated = sorted(name for name in withheld if name in declared)

    return {
        "self_report_version": SELF_REPORT_VERSION,
        "derived": {
            "unset": list(truth.unset),
            "unstructured": list(truth.unstructured),
            "compilable": truth.compilable,
            "approvable": truth.approvable,
        },
        "claimed": {
            "missing": list(claim.believed_missing),
            "unstructured": list(claim.believed_unstructured),
            "ready": claim.believed_ready,
            "unknown_field_names": unknown,
        },
        "overclaimed": overclaimed,
        "overclaimed_by_tier": _by_tier(overclaimed),
        "underclaimed": underclaimed,
        "underclaimed_by_tier": _by_tier(underclaimed),
        "shape_blind": shape_blind,
        "withheld": list(withheld),
        "fabricated": fabricated,
        "readiness": {
            "claimed": claim.believed_ready,
            "derived": truth.approvable,
            "agrees": claim.believed_ready == truth.approvable,
            "false_ready": claim.believed_ready and not truth.approvable,
        },
        "agrees_exactly": not overclaimed and not underclaimed,
    }
