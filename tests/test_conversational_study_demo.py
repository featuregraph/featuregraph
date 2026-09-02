from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

import featuregraph as fg
from featuregraph.study_builder import (
    ConversationalStudySession,
    DraftDecision,
    ExecutionReport,
    OfflineResearchAssistant,
    SessionPhase,
)
from featuregraph.study_builder.conversation import (
    SUPPORTED_STATISTICS,
    _cohere_response_text,
    _cohere_transport_schema,
    _decision_schema,
)
from scripts.conversational_demo_backend import (
    PhysioNetConversationalDemoExecutor,
)
from scripts.run_physionet_wearable_protocol_study import (
    APPROVED_STUDY_CONTRACT,
)


class FakeExecutor:
    def validate(self, candidate: dict[str, object]) -> dict[str, bool]:
        statistics = candidate["measurements"]["statistics"]
        return {
            "supported": set(statistics) <= {"samples", "mean", "median", "min", "max"},
            "required": {"samples", "median"} <= set(statistics),
        }

    def run(
        self,
        approved_contract: fg.ApprovedStudyContract,
        run_directory: Path,
    ) -> ExecutionReport:
        (run_directory / "state_summary.md").write_text(
            "# State summary\n", encoding="utf-8"
        )
        return ExecutionReport(
            eligible_participants=33,
            declared_occurrences=248,
            compiler_checks=99,
            all_checks_passed=True,
            measurement_statistics=tuple(
                approved_contract.contract["measurements"]["statistics"]
            ),
            validation_rows=(
                {"check": "protected", "passed": True, "details": "fixture"},
            ),
            output_files=("state_summary.md",),
        )


class OvercautiousAssistant(OfflineResearchAssistant):
    def draft(self, research_goal: str, clarification: str) -> DraftDecision:
        decision = super().draft(research_goal, clarification)
        return DraftDecision(
            assistant_message="A candidate decision packet is ready for review.",
            research_question=decision.research_question,
            measurement_statistics=(),
            unresolved_questions=("Model uncertainty despite confirmation.",),
            provenance={"mode": "test"},
        )


def build_session(tmp_path: Path) -> ConversationalStudySession:
    return ConversationalStudySession(
        template_contract=APPROVED_STUDY_CONTRACT.contract,
        assistant=OfflineResearchAssistant(),
        executor=FakeExecutor(),
        artifact_directory=tmp_path,
        researcher_authority="test researcher",
    )


def prepare_first_candidate(
    session: ConversationalStudySession,
) -> None:
    first = session.handle_message(
        "How can the two protocol versions share one inspectable representation?"
    )
    assert first.phase is SessionPhase.CLARIFICATION
    second = session.handle_message("Yes, exactly. Preserve those boundaries.")
    assert second.phase is SessionPhase.AWAITING_APPROVAL
    assert second.can_approve


def test_conversation_creates_approved_results_and_checkpoint(tmp_path) -> None:
    session = build_session(tmp_path)
    prepare_first_candidate(session)

    completed = session.approve_and_run()

    assert completed.phase is SessionPhase.EXECUTED
    assert "248 declared occurrences" in completed.message
    assert (tmp_path / "conversation_checkpoint.md").exists()
    assert (tmp_path / "specification_candidate_v1.md").exists()
    assert (tmp_path / "specification_v1.md").exists()
    assert (tmp_path / "results_v1.md").exists()
    approved = fg.load_approved_study_contract(
        tmp_path / "run_v1" / "study_contract_v1.json"
    )
    assert approved.contract["approval"]["authority"] == "test researcher"


def test_conversational_revision_versions_contract_and_comparison(tmp_path) -> None:
    session = build_session(tmp_path)
    prepare_first_candidate(session)
    session.approve_and_run()

    revision = session.handle_message(
        "For the next version, keep only sample counts and medians."
    )
    assert revision.phase is SessionPhase.AWAITING_APPROVAL
    session.approve_and_run()

    revised = fg.load_approved_study_contract(
        tmp_path / "run_v2" / "study_contract_v2.json"
    )
    assert revised.contract["measurements"]["statistics"] == [
        "samples",
        "median",
    ]
    comparison = (tmp_path / "comparison_v1_to_v2.md").read_text()
    assert "mean, min, max" in comparison
    assert "248 | 248" in comparison


def test_unbounded_revision_does_not_create_candidate(tmp_path) -> None:
    session = build_session(tmp_path)
    prepare_first_candidate(session)
    session.approve_and_run()

    response = session.handle_message("Diagnose which participants were stressed.")

    assert response.phase is SessionPhase.EXECUTED
    assert not (tmp_path / "specification_candidate_v2.md").exists()


def test_explicit_confirmation_controls_initial_candidate_state(tmp_path) -> None:
    session = ConversationalStudySession(
        template_contract=APPROVED_STUDY_CONTRACT.contract,
        assistant=OvercautiousAssistant(),
        executor=FakeExecutor(),
        artifact_directory=tmp_path,
        researcher_authority="test researcher",
    )

    session.handle_message(
        "How can the two protocol versions share one inspectable representation?"
    )
    response = session.handle_message("Yes, exactly. Preserve those boundaries.")

    assert response.phase is SessionPhase.AWAITING_APPROVAL
    assert response.can_approve
    assert (tmp_path / "specification_candidate_v1.md").exists()
    assert session.candidate is not None
    assert session.candidate["measurements"]["statistics"] == list(
        ("samples", "mean", "median", "min", "max")
    )
    assert session.candidate["unresolved_questions"] == []


def test_physionet_backend_accepts_only_measurement_revision() -> None:
    executor = PhysioNetConversationalDemoExecutor()
    candidate = fg.study_contract_payload(APPROVED_STUDY_CONTRACT.contract)
    candidate["measurements"]["statistics"] = ["samples", "median"]

    assert all(executor.validate(candidate).values())

    changed_boundary = deepcopy(candidate)
    changed_boundary["sources"]["unassigned_label"] = "rest"
    assert not executor.validate(changed_boundary)[
        "only_measurement_statistics_changed"
    ]


def test_cohere_transport_schema_removes_only_unsupported_constraints() -> None:
    schema = _decision_schema()

    transport_schema = _cohere_transport_schema(schema)

    assert schema["properties"]["assistant_message"]["minLength"] == 1
    assert schema["properties"]["measurement_statistics"]["uniqueItems"] is True
    assert "minLength" not in transport_schema["properties"]["assistant_message"]
    assert "uniqueItems" not in transport_schema["properties"]["measurement_statistics"]
    assert transport_schema["properties"]["measurement_statistics"]["items"] == {
        "type": "string",
        "enum": list(("samples", "mean", "median", "min", "max")),
    }
    assert transport_schema["additionalProperties"] is False

    for property_schema in transport_schema["properties"].values():
        assert "type" in property_schema
        if property_schema["type"] == "array":
            assert "type" in property_schema["items"]


def test_full_schema_constraints_remain_locally_enforced() -> None:
    invalid_payload = {
        "assistant_message": "",
        "research_question": "question",
        "measurement_statistics": ["samples", "samples"],
        "unresolved_questions": [],
    }

    with pytest.raises(ValidationError):
        Draft202012Validator(_decision_schema()).validate(invalid_payload)


def test_cohere_response_text_ignores_thinking_blocks() -> None:
    content = [
        {"type": "thinking", "thinking": "internal reasoning"},
        {"type": "text", "text": '{"question":"What should be preserved?"}'},
    ]

    assert _cohere_response_text(content) == (
        '{"question":"What should be preserved?"}'
    )


def test_cohere_response_text_requires_a_text_block() -> None:
    with pytest.raises(ValueError, match="no text content"):
        _cohere_response_text([{"type": "thinking", "thinking": "internal reasoning"}])


class SilentlyIncompleteAssistant(OfflineResearchAssistant):
    """Names no statistics, and reports no unresolved questions about it.

    The failure the intake wiring exists to catch: a model that leaves a hole
    and does not know it has left one. ``unresolved_questions`` used to come
    straight from the model, so an empty tuple here reached approval.
    """

    def revise(
        self,
        revision: str,
        current_statistics: Sequence[str],
        research_question: str,
    ) -> DraftDecision:
        del revision, current_statistics
        return DraftDecision(
            assistant_message="Revised.",
            research_question=research_question,
            measurement_statistics=(),
            unresolved_questions=(),
            provenance={"mode": "test"},
        )


def test_session_intake_is_seeded_from_the_template_contract(tmp_path) -> None:
    session = build_session(tmp_path)

    assert session.intake.get("title") == "PhysioNet wearable protocol representation"
    assert (
        session.intake.get("claim_limits")
        == (APPROVED_STUDY_CONTRACT.contract["claim_boundaries"])
    )
    # The published contract never wrote these down. They are reported as
    # unstated rather than silently assumed.
    assert "research_question" in session.intake.missing_information
    assert "observation_schema" in session.intake.missing_information


def test_the_conversation_declares_onto_the_intake(tmp_path) -> None:
    session = build_session(tmp_path)
    prepare_first_candidate(session)

    assert session.intake.get("research_question").startswith("How can the two")
    assert session.intake.get("measurements") == list(SUPPORTED_STATISTICS)
    assert session.state()["open_questions"] == []


def test_a_hole_the_model_did_not_report_still_blocks_approval(tmp_path) -> None:
    session = build_session(tmp_path)
    prepare_first_candidate(session)
    session.approve_and_run()
    # Tested on the revision path: an explicit initial confirmation deliberately
    # substitutes the maintained template's statistics, so the first candidate
    # never has this hole to begin with.
    session.assistant = SilentlyIncompleteAssistant()

    response = session.handle_message("Drop the statistics for the next version.")

    assert response.phase is not SessionPhase.AWAITING_APPROVAL
    assert not response.can_approve
    assert session.candidate is None
    assert not (tmp_path / "specification_candidate_v2.md").exists()
    assert any(
        question.startswith("measurements:")
        for question in session.state()["open_questions"]
    )


def test_approval_records_its_own_authority_back_into_the_intake(tmp_path) -> None:
    session = build_session(tmp_path)
    prepare_first_candidate(session)
    seeded = APPROVED_STUDY_CONTRACT.contract["approval"]["authority"]
    assert session.intake.get("provenance")["authority"] == seeded

    session.approve_and_run()

    assert session.intake.get("provenance")["authority"] == "test researcher"


def test_checkpoint_carries_the_intake_and_creates_no_extra_files(tmp_path) -> None:
    session = build_session(tmp_path)
    before = {path.name for path in tmp_path.iterdir()}
    prepare_first_candidate(session)

    checkpoint = (tmp_path / "conversation_checkpoint.md").read_text()
    assert "intake checkpoint v2" in checkpoint
    assert "## PhysioNet wearable protocol representation" in checkpoint
    assert "### Completeness" in checkpoint
    # The intake is rendered into a file that was already written every turn.
    new_files = {path.name for path in tmp_path.iterdir()} - before
    assert not any(name.startswith("intake") for name in new_files)


def test_governed_fields_are_checked_for_existence(tmp_path) -> None:
    with pytest.raises(ValueError, match="sample_rate"):
        ConversationalStudySession(
            template_contract=APPROVED_STUDY_CONTRACT.contract,
            assistant=OfflineResearchAssistant(),
            executor=FakeExecutor(),
            artifact_directory=tmp_path,
            researcher_authority="test researcher",
            governed_intake_fields=("sample_rate",),
        )
