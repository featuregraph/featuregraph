from __future__ import annotations

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
