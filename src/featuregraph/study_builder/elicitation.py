"""Ask a model for an intake, then ask it what it left out.

Two calls per case, kept separate on purpose. The first produces the intake
payload; it is loaded through :meth:`StudyIntake.from_payload`, which is the
only path into an intake, so nothing the model writes can smuggle a
``missing_information`` list in. The second asks the model, shown its own
payload, which fields it believes are unset, which it believes it answered
without structure, and whether the intake is ready to approve. That answer
is a :class:`CompletenessClaim` and is scored, never used.

Every adapter records the same provenance the conversational assistant
already records: model, prompt and response digests, schema digest, and
the provider's response identifier. Adapters return the raw JSON and the
provenance; they do not interpret either.

Refusals and malformed responses are not retried and not repaired. A case
whose response cannot be parsed is recorded as a failed case, because a
harness that quietly fixed the model's output would be scoring itself.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from featuregraph.study_builder.intake import (
    FIELDS,
    INTAKE_SCHEMA_VERSION,
    StudyIntake,
    StudyIntakeError,
)
from featuregraph.study_builder.self_report import CompletenessClaim

ELICITATION_VERSION = 1

_FIELD_NAMES = [f.name for f in FIELDS]

#: The intake payload a model returns. Every field is nullable: ``null`` is
#: "not said", and the model is told so. Lists and mappings are left open
#: because state rules are nested expressions the compiler shapes later.
INTAKE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": _FIELD_NAMES,
    "properties": {
        f.name: (
            {"type": ["string", "null"]}
            if f.kind == "text"
            else {"type": ["array", "object", "null"]}
        )
        for f in FIELDS
    },
}

CLAIM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["believed_missing", "believed_unstructured", "believed_ready"],
    "properties": {
        "believed_missing": {"type": "array", "items": {"type": "string"}},
        "believed_unstructured": {"type": "array", "items": {"type": "string"}},
        "believed_ready": {"type": "boolean"},
    },
}

SYSTEM_PROMPT = (
    "You help a researcher author a FeatureGraph study contract. You "
    "translate what the researcher said into declared fields. You never "
    "invent what they did not say: a field the brief does not answer is "
    "null. Return only JSON."
)


def _field_guide() -> str:
    lines = []
    for f in FIELDS:
        shape = "a string" if f.kind == "text" else "a list or a mapping"
        lines.append(f"- {f.name} ({f.tier}; {shape}): {f.prompt}")
    return "\n".join(lines)


_STRUCTURE_GUIDE = """Compilable fields have a required shape:
- observation_schema: a list of {"column": name, "dtype": ..., "unit": ...}.
  It must list every column the state rules refer to, including columns
  that preprocessing derives from the raw ones; a rule over a column the
  schema does not list cannot compile.
- grouping_and_order: {"group_by": [columns], "order_by": column} or
  {"group_by": [columns], "timeline": {"frequency": "..."}}.
- states_or_labels: either {"state_column": name} or a non-empty list of
  {"name": state, "when": expression}. An expression is a mapping such as
  {"op": "gt", "left": {"column": "x"}, "right": {"parameter": "p"}}; ops are
  gt, ge, lt, le, eq, ne, and, or, neg, abs. Prose is not an expression.
- operator_parameters: a list of {"name": ..., "value": ...} or a mapping.
  A name whose value is null is not a declaration. If the brief names
  thresholds but gives no numbers, leave the whole field null. If the brief
  says there are no parameters, declare an empty list: that is an answer.
- boundary_rules: {"include_first_entry": bool, "include_last_exit": bool}.
- completeness_rules: {"exclusive": bool, "exhaustive": bool}.
An empty list means the researcher said there are none. null means the
researcher did not say."""


def intake_prompt(brief: str) -> str:
    return f"""Read this researcher's brief and declare the study intake.

{brief}

Fields, one JSON key each:
{_field_guide()}

{_STRUCTURE_GUIDE}

Return one JSON object with exactly these keys: {json.dumps(_FIELD_NAMES)}."""


def claim_prompt(brief: str, intake_payload: Mapping[str, Any]) -> str:
    return f"""You declared this intake from the brief below.

Intake you declared:
{json.dumps(intake_payload, indent=1, sort_keys=True)}

Brief:
{brief}

Report, as field names only, which fields you believe are still not declared
(believed_missing), which you declared but in a form the compiler cannot
execute, such as prose where a rule expression was required
(believed_unstructured), and whether the intake is ready for a researcher to
approve (believed_ready). Field names are: {json.dumps(_FIELD_NAMES)}.

Return one JSON object with keys believed_missing, believed_unstructured and
believed_ready."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _schema_sha256(schema: Mapping[str, Any]) -> str:
    return _sha256(json.dumps(schema, sort_keys=True, separators=(",", ":")))


class Elicitor(Protocol):
    """A model boundary: prompt and schema in, JSON text and provenance out."""

    name: str

    def complete(
        self, prompt: str, schema: Mapping[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Return the raw response text and a provenance record."""


@dataclass
class OfflineElicitor:
    """Deterministic stand-in: answers come from a function of the prompt.

    ``respond`` receives the prompt and the schema and returns the payload;
    tests use it to script exactly the disagreement they want to see.
    """

    respond: Callable[[str, Mapping[str, Any]], Mapping[str, Any]]
    name: str = "offline"
    calls: list[str] = field(default_factory=list)

    def complete(
        self, prompt: str, schema: Mapping[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        self.calls.append(prompt)
        text = json.dumps(self.respond(prompt, schema), sort_keys=True)
        return text, {
            "mode": "offline",
            "model": self.name,
            "prompt_sha256": _sha256(prompt),
            "response_sha256": _sha256(text),
            "schema_sha256": _schema_sha256(schema),
            "response_id": None,
        }


def cohere_can_carry(schema: Mapping[str, Any]) -> bool:
    """Whether Cohere's ``json_schema`` subset accepts this schema as written.

    Cohere refuses a ``type`` list that contains ``object`` ("type must not
    be a list that contains `object`"), which is how the intake schema says
    "a list, a mapping, or null". Such a schema is sent as a bare
    ``json_object`` request and validated locally instead, which is the
    validation every response goes through anyway.
    """

    def walk(node: Any) -> bool:
        if isinstance(node, Mapping):
            kind = node.get("type")
            if isinstance(kind, list) and "object" in kind:
                return False
            return all(walk(value) for value in node.values())
        if isinstance(node, list):
            return all(walk(value) for value in node)
        return True

    return walk(schema)


class CohereElicitor:
    """Cohere adapter, the same transport the conversational assistant uses."""

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("A Cohere API key is required.")
        self.api_key = api_key
        self.model = model
        self.name = f"cohere:{model}"

    def complete(
        self, prompt: str, schema: Mapping[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        import cohere

        from featuregraph.study_builder.conversation import (
            _cohere_response_text,
            _cohere_transport_schema,
        )

        transport_schema: dict[str, Any] | None = None
        response_format: dict[str, Any] = {"type": "json_object"}
        if cohere_can_carry(schema):
            transport_schema = _cohere_transport_schema(schema)
            response_format["json_schema"] = transport_schema
        try:
            response = cohere.ClientV2(api_key=self.api_key).chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format=response_format,
                temperature=0,
            )
        except Exception as error:
            status = getattr(error, "status_code", None)
            if status in (401, 403) or isinstance(error, ConnectionError):
                raise ElicitorUnavailable(f"{self.name}: {error}") from error
            raise
        text = _cohere_response_text(response.message.content)
        return text, {
            "mode": "cohere",
            "model": self.model,
            "cohere_sdk_version": cohere.__version__,
            "prompt_sha256": _sha256(prompt),
            "response_sha256": _sha256(text),
            "schema_sha256": _schema_sha256(schema),
            "transport_schema_sha256": (
                _schema_sha256(transport_schema)
                if transport_schema is not None
                else None
            ),
            "transport": "json_schema" if transport_schema else "json_object",
            "response_id": getattr(response, "id", None),
        }


class AnthropicElicitor:
    """Anthropic adapter.

    No server-side fallback is configured, deliberately: a refusal rerun on
    another model would attribute that model's answer to this one. A refusal
    is recorded as a failed case for the named model.
    """

    def __init__(self, model: str = "claude-opus-5", *, api_key: str | None = None):
        self.model = model
        self.api_key = api_key
        self.name = f"anthropic:{model}"

    def complete(
        self, prompt: str, schema: Mapping[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        import anthropic

        try:
            client = (
                anthropic.Anthropic(api_key=self.api_key)
                if self.api_key
                else anthropic.Anthropic()
            )
            response = client.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                output_config={
                    "format": {"type": "json_schema", "schema": dict(schema)}
                },
            )
        except anthropic.AnthropicError as error:
            # Any SDK-level failure, a missing or rejected key, a rejected
            # request shape, no network, is a property of the run and not of
            # the case: it would repeat on all fifty-six.
            raise ElicitorUnavailable(f"{self.name}: {error}") from error
        if response.stop_reason == "refusal":
            details = response.stop_details
            raise ElicitationRefused(
                self.name,
                getattr(details, "category", None),
                getattr(details, "explanation", None),
            )
        text = "".join(block.text for block in response.content if block.type == "text")
        return text, {
            "mode": "anthropic",
            "model": self.model,
            "served_model": getattr(response, "model", None),
            "anthropic_sdk_version": anthropic.__version__,
            "prompt_sha256": _sha256(prompt),
            "response_sha256": _sha256(text),
            "schema_sha256": _schema_sha256(schema),
            "response_id": getattr(response, "id", None),
            "stop_reason": response.stop_reason,
        }


class ElicitorUnavailable(RuntimeError):
    """The provider cannot be called at all: no key, a rejected key, no network.

    Raised through ``elicit`` rather than recorded, because a run that cannot
    reach its model has no cases, only a misconfiguration.
    """


class ElicitationRefused(RuntimeError):
    def __init__(self, model: str, category: Any, explanation: Any) -> None:
        super().__init__(f"{model} refused: {category!r}")
        self.model = model
        self.category = category
        self.explanation = explanation


@dataclass(frozen=True)
class Elicitation:
    """One case's outcome: the intake, the claim, and how each came to be.

    ``error`` is set when a response could not be parsed, validated or loaded
    as an intake. Such a case has no intake and no claim and is reported as
    a failure, not scored.
    """

    intake_payload: Mapping[str, Any] | None
    claim: CompletenessClaim | None
    intake_provenance: Mapping[str, Any]
    claim_provenance: Mapping[str, Any]
    error: str | None = None

    @property
    def intake(self) -> StudyIntake | None:
        if self.intake_payload is None:
            return None
        return StudyIntake.from_payload(self.intake_payload)


def _validate(payload: Any, schema: Mapping[str, Any]) -> None:
    from jsonschema import Draft202012Validator

    Draft202012Validator(schema).validate(payload)


def elicit(brief: str, elicitor: Elicitor) -> Elicitation:
    """Run the two calls for one brief and load what came back."""
    intake_provenance: dict[str, Any] = {}
    claim_provenance: dict[str, Any] = {}
    try:
        text, intake_provenance = elicitor.complete(intake_prompt(brief), INTAKE_SCHEMA)
        payload = json.loads(text)
        _validate(payload, INTAKE_SCHEMA)
        payload["schema_version"] = INTAKE_SCHEMA_VERSION
        StudyIntake.from_payload(payload)  # refuses what the intake refuses
    except ElicitorUnavailable:
        raise
    except ElicitationRefused as refused:
        return Elicitation(None, None, intake_provenance, {}, error=str(refused))
    except (ValueError, StudyIntakeError) as error:
        return Elicitation(None, None, intake_provenance, {}, error=f"intake: {error}")
    except Exception as error:  # jsonschema.ValidationError and provider errors
        return Elicitation(None, None, intake_provenance, {}, error=f"intake: {error}")

    try:
        text, claim_provenance = elicitor.complete(
            claim_prompt(brief, payload), CLAIM_SCHEMA
        )
        claimed = json.loads(text)
        _validate(claimed, CLAIM_SCHEMA)
        claim = CompletenessClaim(
            believed_missing=tuple(claimed["believed_missing"]),
            believed_unstructured=tuple(claimed["believed_unstructured"]),
            believed_ready=bool(claimed["believed_ready"]),
            provenance=claim_provenance,
        )
    except ElicitationRefused as refused:
        return Elicitation(
            payload, None, intake_provenance, claim_provenance, str(refused)
        )
    except Exception as error:
        return Elicitation(
            payload, None, intake_provenance, claim_provenance, f"claim: {error}"
        )
    return Elicitation(payload, claim, intake_provenance, claim_provenance)
