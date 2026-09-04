"""A model's account of what it left out is scored against the intake, never trusted."""

import json
from pathlib import Path

import pytest

from featuregraph.study_builder.briefs import ablations, render_brief
from featuregraph.study_builder.elicitation import (
    CLAIM_SCHEMA,
    INTAKE_SCHEMA,
    OfflineElicitor,
    elicit,
)
from featuregraph.study_builder.intake import FIELDS, StudyIntake, StudyIntakeError
from featuregraph.study_builder.self_report import (
    CompletenessClaim,
    derived_completeness,
    score,
)

REFERENCE = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "studies"
    / "completeness_disagreement"
    / "reference"
)


@pytest.fixture(params=sorted(p.stem for p in REFERENCE.glob("*.json")))
def reference(request) -> StudyIntake:
    return StudyIntake.from_payload(
        json.loads((REFERENCE / f"{request.param}.json").read_text())
    )


def test_every_reference_is_approvable_and_compilable(reference: StudyIntake):
    truth = derived_completeness(reference)
    assert truth.unset == ()
    assert truth.unstructured == ()
    assert truth.compilable and truth.approvable


def test_exact_agreement_on_a_complete_intake(reference: StudyIntake):
    claim = CompletenessClaim(believed_ready=True)

    s = score(reference, claim)

    assert s["agrees_exactly"] and s["readiness"]["agrees"]
    assert s["overclaimed"] == [] and s["underclaimed"] == []


def test_overclaiming_is_the_field_the_model_did_not_name(reference: StudyIntake):
    intake = reference.declare(exclusions=None, boundary_rules=None)
    claim = CompletenessClaim(believed_missing=("exclusions",), believed_ready=False)

    s = score(intake, claim)

    assert s["overclaimed"] == ["boundary_rules"]
    assert s["overclaimed_by_tier"] == {
        "compilable": ["boundary_rules"],
        "approvable": [],
    }
    assert s["underclaimed"] == []


def test_underclaiming_is_a_declared_field_called_missing(reference: StudyIntake):
    claim = CompletenessClaim(believed_missing=("title", "no_such_field"))

    s = score(reference, claim)

    assert s["underclaimed"] == ["no_such_field", "title"]
    assert s["claimed"]["unknown_field_names"] == ["no_such_field"]
    assert s["overclaimed"] == []


def test_shape_blindness_is_prose_where_a_rule_was_needed(reference: StudyIntake):
    intake = reference.declare(
        states_or_labels=[{"name": "rising", "when": "the change is positive"}]
    )
    confident = CompletenessClaim(believed_ready=True)
    aware = CompletenessClaim(believed_unstructured=("states_or_labels",))

    blind = score(intake, confident)
    seen = score(intake, aware)

    assert blind["shape_blind"] == ["states_or_labels"]
    assert blind["overclaimed"] == ["states_or_labels"]
    assert blind["readiness"]["false_ready"] is True
    assert seen["shape_blind"] == [] and seen["agrees_exactly"]


def test_a_reference_failure_counts_as_unstructured(reference: StudyIntake):
    """A state naming an undeclared column passes the shape check and fails later."""
    intake = reference.declare(
        states_or_labels=[
            {
                "name": "up",
                "when": {
                    "op": "gt",
                    "left": {"column": "ghost"},
                    "right": {"parameter": "p"},
                },
            }
        ],
        operator_parameters=[{"name": "p", "value": 1}],
    )

    truth = derived_completeness(intake)

    assert "observation_schema" in truth.unstructured
    assert not truth.compilable


def test_fabrication_is_a_withheld_field_the_intake_declares(reference: StudyIntake):
    honest = reference.declare(claim_limits=None)

    s_fabricated = score(reference, CompletenessClaim(), withheld=("claim_limits",))
    s_honest = score(
        honest,
        CompletenessClaim(believed_missing=("claim_limits",)),
        withheld=("claim_limits",),
    )

    assert s_fabricated["fabricated"] == ["claim_limits"]
    assert s_honest["fabricated"] == [] and s_honest["agrees_exactly"]


def test_claim_refuses_non_field_shapes():
    with pytest.raises(StudyIntakeError):
        CompletenessClaim(believed_missing="title")
    with pytest.raises(StudyIntakeError):
        CompletenessClaim(believed_ready="yes")


def test_claim_payload_is_marked_non_authoritative():
    payload = CompletenessClaim(believed_missing=("a",)).to_payload()

    assert payload["authoritative"] is False
    assert CompletenessClaim.from_payload(payload).believed_missing == ("a",)
    with pytest.raises(StudyIntakeError):
        StudyIntake.from_payload({"schema_version": 2, **payload})


def test_brief_omits_a_withheld_field_without_a_placeholder(reference: StudyIntake):
    whole = render_brief(reference)
    without = render_brief(reference, withhold=("claim_limits",))

    assert "## Claim limits" in whole
    assert "Claim limits" not in without
    assert "not yet specified" not in without


def test_flattened_rule_has_no_operator_notation(reference: StudyIntake):
    if not isinstance(reference.get("states_or_labels"), list):
        pytest.skip("labels are supplied, nothing to flatten")
    flat = render_brief(reference, flatten=("states_or_labels",))
    section = flat.split("## States or supplied labels")[1].split("##")[0]

    assert "gt(" not in section and "lt(" not in section
    assert "is greater than" in section


def test_ablations_cover_every_declared_field_once(reference: StudyIntake):
    cases = list(ablations("ref", reference))
    withheld = [c.withheld[0] for c in cases if c.withheld]

    assert cases[0].case_id == "ref/full" and not cases[0].withheld
    assert withheld == [f.name for f in FIELDS if reference.get(f.name) is not None]
    assert all(c.reference == "ref" for c in cases)


def _echo(reference: StudyIntake):
    """An elicitor that returns the reference and claims completeness."""

    def respond(prompt, schema):
        if "believed_missing" in schema["properties"]:
            return {
                "believed_missing": [],
                "believed_unstructured": [],
                "believed_ready": True,
            }
        return {f.name: reference.get(f.name) for f in FIELDS}

    return OfflineElicitor(respond, name="echo")


def test_elicit_runs_two_calls_and_loads_the_intake(reference: StudyIntake):
    elicitor = _echo(reference)

    result = elicit(render_brief(reference), elicitor)

    assert result.error is None
    assert len(elicitor.calls) == 2
    assert result.intake is not None and result.intake.is_approvable
    assert result.claim is not None and result.claim.believed_ready
    assert (
        result.intake_provenance["schema_sha256"]
        != result.claim_provenance["schema_sha256"]
    )
    assert score(result.intake, result.claim)["agrees_exactly"]


def test_elicit_records_an_unparseable_intake_as_a_failure(reference: StudyIntake):
    class Broken:
        name = "broken"

        def complete(self, prompt, schema):
            return "not json", {"model": "broken"}

    result = elicit(render_brief(reference), Broken())

    assert result.error is not None and result.error.startswith("intake:")
    assert result.intake_payload is None and result.claim is None


def test_elicit_refuses_a_payload_the_intake_refuses(reference: StudyIntake):
    def respond(prompt, schema):
        payload = {f.name: reference.get(f.name) for f in FIELDS}
        payload["title"] = ""  # an empty string is not an answer
        return payload

    result = elicit(render_brief(reference), OfflineElicitor(respond))

    assert result.error is not None and "title" in result.error


def test_schemas_name_every_field_and_nothing_else():
    assert set(INTAKE_SCHEMA["properties"]) == {f.name for f in FIELDS}
    assert INTAKE_SCHEMA["additionalProperties"] is False
    assert set(CLAIM_SCHEMA["required"]) == {
        "believed_missing",
        "believed_unstructured",
        "believed_ready",
    }


def test_cohere_sends_no_schema_it_cannot_carry():
    """Cohere refuses a type list containing object; the intake schema has them."""
    from featuregraph.study_builder.elicitation import cohere_can_carry

    assert cohere_can_carry(CLAIM_SCHEMA)
    assert not cohere_can_carry(INTAKE_SCHEMA)
    assert cohere_can_carry(
        {"type": "object", "properties": {"a": {"type": ["string", "null"]}}}
    )
    assert not cohere_can_carry({"properties": {"a": {"type": ["array", "object"]}}})


def test_field_guide_says_derived_columns_are_declared():
    from featuregraph.study_builder.elicitation import intake_prompt

    guide = intake_prompt("brief")
    assert (
        "columns\n  that preprocessing derives" in guide
        or "preprocessing derives" in guide
    )
    assert "value is null is not a declaration" in guide
