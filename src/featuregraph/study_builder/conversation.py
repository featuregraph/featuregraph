"""Bounded conversational authoring for deterministic FeatureGraph studies."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from featuregraph.contracts.study_contract import (
    ApprovedStudyContract,
    approve_study_contract,
    load_approved_study_contract,
    study_contract_payload,
)
from featuregraph.study_builder.intake import (
    FIELDS_BY_NAME,
    StudyIntake,
    intake_from_study_contract,
    render_checkpoint,
)

#: Intake fields this conversation is answerable for. The template contract
#: supplies the rest, and a hole in one of these blocks approval no matter what
#: the assistant claims about its own completeness.
GOVERNED_INTAKE_FIELDS = ("research_question", "measurements")

SUPPORTED_STATISTICS = ("samples", "mean", "median", "min", "max")
REQUIRED_STATISTICS = ("samples", "median")
COHERE_UNSUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "maximum",
        "maxItems",
        "maxLength",
        "minimum",
        "minItems",
        "minLength",
        "uniqueItems",
    }
)


def _cohere_transport_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Return Cohere's supported subset while preserving the source schema."""

    def compatible(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                key: compatible(item)
                for key, item in value.items()
                if key not in COHERE_UNSUPPORTED_SCHEMA_KEYWORDS
            }
        if isinstance(value, list):
            return [compatible(item) for item in value]
        return deepcopy(value)

    return compatible(schema)


def _schema_sha256(schema: Mapping[str, Any]) -> str:
    encoded = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _cohere_response_text(content: Sequence[Any] | None) -> str:
    """Extract text blocks while ignoring optional Cohere reasoning blocks."""

    text_blocks: list[str] = []
    for item in content or ():
        if isinstance(item, Mapping):
            item_type = item.get("type")
            item_text = item.get("text")
        else:
            item_type = getattr(item, "type", None)
            item_text = getattr(item, "text", None)
        if item_type == "text" and isinstance(item_text, str):
            text_blocks.append(item_text)
    if not text_blocks:
        raise ValueError("Cohere returned no text content.")
    return "".join(text_blocks)


class SessionPhase(str, Enum):
    """The explicit authority state of one conversational study session."""

    DISCOVERY = "discovery"
    CLARIFICATION = "clarification"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTED = "executed"


@dataclass(frozen=True)
class ArtifactLink:
    """One user-visible artifact emitted by the conversation."""

    label: str
    path: str


@dataclass(frozen=True)
class DraftDecision:
    """A model proposal that remains ineligible for execution."""

    assistant_message: str
    research_question: str
    measurement_statistics: tuple[str, ...]
    unresolved_questions: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionReport:
    """Small, model-independent summary returned by a study executor."""

    eligible_participants: int
    declared_occurrences: int
    compiler_checks: int
    all_checks_passed: bool
    measurement_statistics: tuple[str, ...]
    validation_rows: tuple[Mapping[str, Any], ...]
    output_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConversationResponse:
    """Serializable response consumed by the browser interface."""

    message: str
    phase: SessionPhase
    artifacts: tuple[ArtifactLink, ...] = ()
    can_approve: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-ready representation."""

        return {
            "message": self.message,
            "phase": self.phase.value,
            "artifacts": [asdict(artifact) for artifact in self.artifacts],
            "can_approve": self.can_approve,
        }


class ResearchAssistant(Protocol):
    """Model boundary used by the deterministic session controller."""

    def clarify(self, research_goal: str) -> str:
        """Ask one question that materially affects the study contract."""

    def draft(self, research_goal: str, clarification: str) -> DraftDecision:
        """Propose a first candidate from the conversation."""

    def revise(
        self,
        request: str,
        current_statistics: Sequence[str],
        research_question: str,
    ) -> DraftDecision:
        """Propose a revision without granting execution authority."""


class StudyExecutor(Protocol):
    """Deterministic backend boundary for a conversational study."""

    def validate(self, candidate: Mapping[str, Any]) -> Mapping[str, bool]:
        """Return the deterministic checks required before approval."""

    def run(
        self,
        approved_contract: ApprovedStudyContract,
        run_directory: Path,
    ) -> ExecutionReport:
        """Execute an approved contract and write its output files."""


class OfflineResearchAssistant:
    """Frozen assistant that keeps the demonstration runnable without an API."""

    mode = "offline_frozen_example"

    def clarify(self, research_goal: str) -> str:
        """Return the maintained clarification boundary for the demo."""

        del research_goal
        return (
            "Should FeatureGraph use only the externally recorded protocol tags "
            "as boundaries, leave time outside declared stages unassigned, and "
            "treat self-reports and sensor values as measurements rather than "
            "labels inferred by the system?"
        )

    def draft(self, research_goal: str, clarification: str) -> DraftDecision:
        """Prepare the maintained full-measurement candidate."""

        unresolved = (
            ()
            if _looks_affirmative(clarification)
            else ("Confirm the external-boundary and unassigned-time policies.",)
        )
        return DraftDecision(
            assistant_message=(
                "I translated our discussion into a candidate specification. "
                "It preserves the external tag boundaries, leaves undeclared "
                "time unassigned, and measures sample count, mean, median, "
                "minimum, and maximum at each native sensor rate."
            ),
            research_question=research_goal.strip(),
            measurement_statistics=SUPPORTED_STATISTICS,
            unresolved_questions=unresolved,
            provenance={"mode": self.mode, "operation": "draft"},
        )

    def revise(
        self,
        request: str,
        current_statistics: Sequence[str],
        research_question: str,
    ) -> DraftDecision:
        """Interpret a narrow measurement-statistics revision deterministically."""

        statistics = _statistics_from_revision(request, current_statistics)
        if statistics is None:
            return DraftDecision(
                assistant_message=(
                    "This first demo can revise the reported measurement "
                    "statistics. Please name any of: sample count, mean, median, "
                    "minimum, or maximum."
                ),
                research_question=research_question,
                measurement_statistics=tuple(current_statistics),
                unresolved_questions=(
                    "The requested revision is outside the bounded demo vocabulary.",
                ),
                provenance={"mode": self.mode, "operation": "revision"},
            )

        missing_required = [
            statistic
            for statistic in REQUIRED_STATISTICS
            if statistic not in statistics
        ]
        if missing_required:
            return DraftDecision(
                assistant_message=(
                    "The protected study requires sample counts and medians for "
                    "its validation and comparison. Please keep both in the "
                    "candidate specification."
                ),
                research_question=research_question,
                measurement_statistics=statistics,
                unresolved_questions=(
                    "Required statistics are missing: " + ", ".join(missing_required),
                ),
                provenance={"mode": self.mode, "operation": "revision"},
            )

        labels = ", ".join(statistics)
        return DraftDecision(
            assistant_message=(
                "I prepared a revised candidate using only these measurement "
                f"statistics: {labels}. The protocol boundaries, occurrences, "
                "joins, exclusions, and claim limits are unchanged."
            ),
            research_question=research_question,
            measurement_statistics=statistics,
            provenance={"mode": self.mode, "operation": "revision"},
        )


class CohereResearchAssistant:
    """Cohere adapter that produces proposals but cannot approve or execute."""

    def __init__(self, api_key: str, model: str = "command-a-plus-05-2026") -> None:
        if not api_key:
            raise ValueError("A Cohere API key is required.")
        self.api_key = api_key
        self.model = model

    def _json(
        self,
        prompt: str,
        schema: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        import cohere
        from jsonschema import Draft202012Validator

        transport_schema = _cohere_transport_schema(schema)
        response = cohere.ClientV2(api_key=self.api_key).chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You help a researcher author a FeatureGraph study. "
                        "Separate researcher authority from model proposals. "
                        "Never approve, execute, infer stress, claim causality, "
                        "or assign scientific validity. Return only JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_object",
                "json_schema": transport_schema,
            },
            temperature=0,
        )
        response_text = _cohere_response_text(response.message.content)
        payload = json.loads(response_text)
        Draft202012Validator(schema).validate(payload)
        return payload, {
            "mode": "cohere",
            "model": self.model,
            "cohere_sdk_version": cohere.__version__,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "response_sha256": hashlib.sha256(response_text.encode()).hexdigest(),
            "schema_sha256": _schema_sha256(schema),
            "transport_schema_sha256": _schema_sha256(transport_schema),
            "response_id": getattr(response, "id", None),
        }

    def clarify(self, research_goal: str) -> str:
        """Ask one bounded clarification question through Cohere."""

        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["question"],
            "properties": {"question": {"type": "string", "minLength": 1}},
        }
        prompt = f"""The researcher described this goal:
{research_goal}

Ask exactly one friendly question confirming whether external protocol tags are
the only boundaries, undeclared time remains unassigned, and self-reports plus
sensor values remain measurements rather than inferred state labels. Do not ask
for unrelated information."""
        payload, _ = self._json(prompt, schema)
        return str(payload["question"])

    def draft(self, research_goal: str, clarification: str) -> DraftDecision:
        """Draft a constrained candidate decision packet through Cohere."""

        schema = _decision_schema()
        prompt = f"""Prepare a candidate decision packet for the protected
PhysioNet wearable protocol demonstration.

Research goal:
{research_goal}

Researcher clarification:
{clarification}

The maintained template uses external protocol tags as boundaries, leaves
undeclared time unassigned, treats self-reports and native-rate HR, EDA, and
temperature as measurements, and initially reports samples, mean, median, min,
and max. Preserve those decisions only when the clarification confirms them.
If the clarification explicitly confirms all of them, unresolved_questions must
be empty. Otherwise, put the remaining uncertainty in unresolved_questions and
ask for it in assistant_message. Say that a candidate is ready for review only
when unresolved_questions is empty."""
        payload, provenance = self._json(prompt, schema)
        return _decision_from_payload(payload, provenance)

    def revise(
        self,
        request: str,
        current_statistics: Sequence[str],
        research_question: str,
    ) -> DraftDecision:
        """Translate a free-text measurement revision through Cohere."""

        schema = _decision_schema()
        prompt = f"""Interpret one revision to a protected FeatureGraph study.
Only measurement statistics may change. Supported values are samples, mean,
median, min, and max. Samples and median are required. Do not change protocol
boundaries, occurrences, joins, exclusions, or claim boundaries.

Research question: {research_question}
Current statistics: {json.dumps(list(current_statistics))}
Researcher request: {request}

Return the complete proposed statistics list. Put unsupported or ambiguous
requests in unresolved_questions. Briefly explain the proposed change in
assistant_message."""
        payload, provenance = self._json(prompt, schema)
        decision = _decision_from_payload(payload, provenance)
        invalid = [
            statistic
            for statistic in decision.measurement_statistics
            if statistic not in SUPPORTED_STATISTICS
        ]
        missing = [
            statistic
            for statistic in REQUIRED_STATISTICS
            if statistic not in decision.measurement_statistics
        ]
        if invalid or missing:
            questions = list(decision.unresolved_questions)
            if invalid:
                questions.append("Unsupported statistics: " + ", ".join(invalid))
            if missing:
                questions.append("Required statistics missing: " + ", ".join(missing))
            return DraftDecision(
                assistant_message=decision.assistant_message,
                research_question=research_question,
                measurement_statistics=decision.measurement_statistics,
                unresolved_questions=tuple(questions),
                provenance=provenance,
            )
        return DraftDecision(
            assistant_message=decision.assistant_message,
            research_question=research_question,
            measurement_statistics=decision.measurement_statistics,
            unresolved_questions=decision.unresolved_questions,
            provenance=provenance,
        )


class ConversationalStudySession:
    """Own one conversation, its candidates, approvals, runs, and artifacts."""

    def __init__(
        self,
        *,
        template_contract: Mapping[str, Any],
        assistant: ResearchAssistant,
        executor: StudyExecutor,
        artifact_directory: Path,
        researcher_authority: str,
        governed_intake_fields: Sequence[str] = GOVERNED_INTAKE_FIELDS,
    ) -> None:
        self.template_payload = study_contract_payload(template_contract)
        unknown = sorted(set(governed_intake_fields) - set(FIELDS_BY_NAME))
        if unknown:
            raise ValueError(f"Unknown intake fields to govern: {unknown}.")
        self.governed_intake_fields = tuple(governed_intake_fields)
        # Seeded from the template rather than started empty, so the fields a
        # published contract already declares are not re-asked, and the ones it
        # never wrote down are visible instead of assumed.
        self.intake: StudyIntake = intake_from_study_contract(template_contract)
        self.assistant = assistant
        self.executor = executor
        self.artifact_directory = artifact_directory.resolve()
        self.artifact_directory.mkdir(parents=True, exist_ok=True)
        self.researcher_authority = researcher_authority
        self.phase = SessionPhase.DISCOVERY
        self.messages: list[dict[str, str]] = [
            {
                "role": "assistant",
                "content": (
                    "Tell me what you want to understand about the preloaded "
                    "PhysioNet wearable protocol study. I will help turn the "
                    "discussion into an inspectable FeatureGraph specification."
                ),
            }
        ]
        self.research_goal = ""
        self.research_question = ""
        self.candidate: dict[str, Any] | None = None
        self.candidate_provenance: Mapping[str, Any] = {}
        self.version = 0
        self.reports: list[ExecutionReport] = []
        self.approved_payloads: list[dict[str, Any]] = []
        self._write_checkpoint()

    def state(self) -> dict[str, Any]:
        """Return the browser-facing session state."""

        return {
            "phase": self.phase.value,
            "messages": deepcopy(self.messages),
            "can_approve": self.phase is SessionPhase.AWAITING_APPROVAL,
            "version": self.version,
            "artifacts": [asdict(link) for link in self._current_artifact_links()],
            "intake": self.intake.to_payload(),
            "open_questions": self._governed_gaps(),
        }

    def handle_message(self, message: str) -> ConversationResponse:
        """Advance the bounded conversation by one researcher message."""

        cleaned = message.strip()
        if not cleaned:
            return self._respond("Please enter a research question or revision.")
        self.messages.append({"role": "user", "content": cleaned})

        if self.phase is SessionPhase.DISCOVERY:
            self.research_goal = cleaned
            reply = self.assistant.clarify(cleaned)
            self.phase = SessionPhase.CLARIFICATION
            return self._respond(reply)

        if self.phase is SessionPhase.CLARIFICATION:
            decision = self.assistant.draft(self.research_goal, cleaned)
            decision = _apply_explicit_initial_confirmation(
                decision,
                research_goal=self.research_goal,
                clarification=cleaned,
            )
            return self._prepare_candidate(decision)

        if self.phase is SessionPhase.AWAITING_APPROVAL:
            return self._respond(
                "The candidate cannot approve itself. Review the linked "
                "specification, then use “Approve and run” to record researcher "
                "authority."
            )

        current_statistics = self.approved_payloads[-1]["measurements"]["statistics"]
        decision = self.assistant.revise(
            cleaned,
            current_statistics,
            self.research_question,
        )
        if decision.unresolved_questions:
            return self._respond(decision.assistant_message)
        return self._prepare_candidate(decision)

    def approve_and_run(self) -> ConversationResponse:
        """Record explicit researcher approval and invoke the deterministic backend."""

        if self.phase is not SessionPhase.AWAITING_APPROVAL or self.candidate is None:
            return self._respond("There is no candidate awaiting approval.")

        validations = dict(self.executor.validate(self.candidate))
        approved = approve_study_contract(
            self.candidate,
            authority=self.researcher_authority,
            validation_results=validations,
        )
        next_version = self.version + 1
        run_directory = self.artifact_directory / f"run_v{next_version}"
        run_directory.mkdir(parents=True, exist_ok=True)
        contract_path = run_directory / f"study_contract_v{next_version}.json"
        contract_path.write_text(
            json.dumps(approved, indent=2) + "\n",
            encoding="utf-8",
        )
        loaded = load_approved_study_contract(contract_path)
        report = self.executor.run(loaded, run_directory)

        self.version = next_version
        self.reports.append(report)
        self.approved_payloads.append(study_contract_payload(approved))
        self.intake = self.intake.declare(
            provenance=intake_from_study_contract(approved).get("provenance")
        )
        self._write_specification(
            self.approved_payloads[-1],
            self.version,
            status="approved and executed",
        )
        self._write_results(report, self.version, loaded.sha256)
        if len(self.reports) > 1:
            self._write_comparison(
                self.reports[-2],
                self.reports[-1],
                self.version - 1,
                self.version,
            )

        self.phase = SessionPhase.EXECUTED
        self.candidate = None
        reply = (
            f"Version {self.version} is complete. FeatureGraph preserved "
            f"{report.declared_occurrences} declared occurrences across "
            f"{report.eligible_participants} eligible participants, and all "
            f"{report.compiler_checks} compiler checks passed. I created the "
            "approved specification and results summary below. Tell me what "
            "you would like to change."
        )
        return self._respond(reply)

    def _declare_from(self, decision: DraftDecision) -> None:
        """Record a proposal as intake declarations, not as settled fact."""
        statistics = list(decision.measurement_statistics)
        self.intake = self.intake.declare(
            research_question=decision.research_question.strip() or None,
            # An empty list is a researcher saying "there are none". Coming from
            # an assistant that named no statistics it means the opposite -- the
            # question was not answered -- so it is recorded as unanswered.
            measurements=statistics or None,
        )

    def _governed_gaps(self) -> list[str]:
        """Open questions derived from the intake, in this session's own fields.

        The assistant reports its own unresolved questions, and an assistant
        that fails to notice a hole reports none. These are computed from what
        is actually declared, so the two cannot quietly disagree.
        """
        outstanding = set(self.intake.missing_information) | set(
            self.intake.unstructured
        )
        return [
            f"{name}: {FIELDS_BY_NAME[name].prompt}"
            for name in self.governed_intake_fields
            if name in outstanding
        ]

    def _prepare_candidate(self, decision: DraftDecision) -> ConversationResponse:
        self._declare_from(decision)
        candidate = deepcopy(
            self.approved_payloads[-1]
            if self.approved_payloads
            else self.template_payload
        )
        candidate["measurements"]["statistics"] = list(decision.measurement_statistics)
        unresolved = list(decision.unresolved_questions) + self._governed_gaps()
        candidate["unresolved_questions"] = unresolved
        self.candidate = candidate
        self.candidate_provenance = decision.provenance
        self.research_question = decision.research_question

        if unresolved:
            self.candidate = None
            return self._respond(decision.assistant_message)

        validations = dict(self.executor.validate(candidate))
        candidate_version = self.version + 1
        self._write_specification(
            candidate,
            candidate_version,
            status="candidate awaiting researcher approval",
            validations=validations,
        )
        provenance_path = self.artifact_directory / (
            f"model_provenance_v{candidate_version}.json"
        )
        provenance_path.write_text(
            json.dumps(dict(decision.provenance), indent=2) + "\n",
            encoding="utf-8",
        )
        self.phase = SessionPhase.AWAITING_APPROVAL
        return self._respond(
            decision.assistant_message
            + " Review the candidate specification. Nothing will execute until "
            "you explicitly approve it."
        )

    def _respond(self, message: str) -> ConversationResponse:
        self.messages.append({"role": "assistant", "content": message})
        self._write_checkpoint()
        return ConversationResponse(
            message=message,
            phase=self.phase,
            artifacts=self._current_artifact_links(),
            can_approve=self.phase is SessionPhase.AWAITING_APPROVAL,
        )

    def _write_checkpoint(self) -> None:
        lines = [
            "# Conversational study checkpoint",
            "",
            f"Current phase: `{self.phase.value}`",
            "",
            "The conversation may propose a study specification. Only an explicit "
            "researcher approval can make a validated candidate executable.",
            "",
            "## Conversation",
            "",
        ]
        for message in self.messages:
            speaker = "Researcher" if message["role"] == "user" else "Assistant"
            lines.extend([f"### {speaker}", "", message["content"], ""])
        # Rendered into the checkpoint that is already written every turn,
        # rather than into a file of its own. The intake changes on every turn,
        # and a per-turn artifact for it would be one more thing to reconcile.
        lines.extend(["", render_checkpoint(self.intake, level=2)])
        (self.artifact_directory / "conversation_checkpoint.md").write_text(
            "\n".join(lines).rstrip() + "\n",
            encoding="utf-8",
        )

    def _write_specification(
        self,
        payload: Mapping[str, Any],
        version: int,
        *,
        status: str,
        validations: Mapping[str, bool] | None = None,
    ) -> None:
        statistics = payload["measurements"]["statistics"]
        protocols = payload["protocol_versions"]
        lines = [
            f"# FeatureGraph study specification v{version}",
            "",
            f"Status: **{status}**",
            "",
            "## Research question",
            "",
            self.research_question or self.research_goal,
            "",
            "## Construction decisions",
            "",
            "- Use only the dataset's externally recorded protocol tags as boundaries.",
            "- Leave time outside declared protocol stages unassigned.",
            "- Treat self-reports as joined measurements, not inferred labels.",
            "- Preserve HR, EDA, and temperature at their native sampling rates.",
            f"- Report these statistics: {', '.join(statistics)}.",
            "",
            "## Declared protocol occurrences",
            "",
        ]
        for cohort, protocol in protocols.items():
            states = [item["state"] for item in protocol["occurrences"]]
            lines.append(f"- `{cohort}`: {', '.join(states)}")
        lines.extend(["", "## Claim boundaries", ""])
        lines.extend(f"- {boundary}" for boundary in payload["claim_boundaries"])
        if validations is not None:
            lines.extend(["", "## Candidate validation", ""])
            lines.extend(
                f"- {'PASS' if passed else 'FAIL'} — `{name}`"
                for name, passed in validations.items()
            )
        filename = (
            f"specification_v{version}.md"
            if status.startswith("approved")
            else f"specification_candidate_v{version}.md"
        )
        (self.artifact_directory / filename).write_text(
            "\n".join(lines).rstrip() + "\n",
            encoding="utf-8",
        )

    def _write_results(
        self,
        report: ExecutionReport,
        version: int,
        contract_sha256: str,
    ) -> None:
        lines = [
            f"# FeatureGraph conversational study results v{version}",
            "",
            "> Demonstration result produced from a protected, network-free fixture. "
            "It verifies the workflow and does not constitute a physiological finding.",
            "",
            "## Execution summary",
            "",
            f"- Eligible participants: **{report.eligible_participants}**",
            f"- Declared protocol occurrences: **{report.declared_occurrences}**",
            f"- Compiler checks: **{report.compiler_checks}**",
            f"- All checks passed: **{report.all_checks_passed}**",
            "- Measurement statistics: " + ", ".join(report.measurement_statistics),
            f"- Approved contract SHA-256: `{contract_sha256}`",
            "",
            "## Validation",
            "",
            "| Check | Passed | Details |",
            "|---|---:|---|",
        ]
        for row in report.validation_rows:
            details = str(row.get("details", "")).replace("|", "\\|")
            lines.append(
                f"| {row.get('check', '')} | {row.get('passed', False)} | {details} |"
            )
        lines.extend(["", "## Interpretation boundary", ""])
        lines.extend(
            [
                "The run shows that the approved representation was executed "
                "consistently and passed its declared structural checks.",
                "",
                "It does not show that stress was detected, that the physiological "
                "measurements are causal, or that the protocol labels are "
                "clinically valid.",
            ]
        )
        (self.artifact_directory / f"results_v{version}.md").write_text(
            "\n".join(lines).rstrip() + "\n",
            encoding="utf-8",
        )

    def _write_comparison(
        self,
        previous: ExecutionReport,
        current: ExecutionReport,
        previous_version: int,
        current_version: int,
    ) -> None:
        removed = [
            value
            for value in previous.measurement_statistics
            if value not in current.measurement_statistics
        ]
        added = [
            value
            for value in current.measurement_statistics
            if value not in previous.measurement_statistics
        ]
        lines = [
            f"# Study comparison: v{previous_version} → v{current_version}",
            "",
            "## Approved specification change",
            "",
            f"- Statistics removed: {', '.join(removed) if removed else 'none'}",
            f"- Statistics added: {', '.join(added) if added else 'none'}",
            "- Protocol boundaries, occurrences, joins, exclusions, and claim "
            "limits: unchanged",
            "",
            "## Execution comparison",
            "",
            "| Result | Previous | Current |",
            "|---|---:|---:|",
            (
                f"| Declared occurrences | {previous.declared_occurrences} | "
                f"{current.declared_occurrences} |"
            ),
            (
                f"| Compiler checks | {previous.compiler_checks} | "
                f"{current.compiler_checks} |"
            ),
            (
                f"| All checks passed | {previous.all_checks_passed} | "
                f"{current.all_checks_passed} |"
            ),
            "",
            "The revision changed which measurements were reported; it did not "
            "change which protocol occurrences FeatureGraph constructed.",
        ]
        path = self.artifact_directory / (
            f"comparison_v{previous_version}_to_v{current_version}.md"
        )
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    def _current_artifact_links(self) -> tuple[ArtifactLink, ...]:
        files = sorted(
            self.artifact_directory.rglob("*"),
            key=lambda path: path.stat().st_mtime,
        )
        return tuple(
            ArtifactLink(
                label=str(path.relative_to(self.artifact_directory)),
                path=str(path.relative_to(self.artifact_directory)),
            )
            for path in files
            if path.is_file() and path.suffix in {".md", ".json"}
        )


def _looks_affirmative(value: str) -> bool:
    tokens = set(re.findall(r"[a-z]+", value.lower()))
    return bool(tokens & {"yes", "correct", "agree", "confirmed", "exactly"})


def _apply_explicit_initial_confirmation(
    decision: DraftDecision,
    *,
    research_goal: str,
    clarification: str,
) -> DraftDecision:
    """Bind an explicit confirmation to the maintained initial template."""

    if not _looks_affirmative(clarification):
        return decision
    provenance = dict(decision.provenance)
    provenance["confirmation_rule"] = "explicit_researcher_affirmation"
    return DraftDecision(
        assistant_message=decision.assistant_message,
        research_question=decision.research_question or research_goal.strip(),
        measurement_statistics=SUPPORTED_STATISTICS,
        unresolved_questions=(),
        provenance=provenance,
    )


def _statistics_from_revision(
    request: str, current_statistics: Sequence[str]
) -> tuple[str, ...] | None:
    lowered = request.lower()
    aliases = {
        "samples": ("sample", "samples", "count", "counts"),
        "mean": ("mean", "means", "average", "averages"),
        "median": ("median", "medians"),
        "min": ("min", "minimum", "minimums", "minima"),
        "max": ("max", "maximum", "maximums", "maxima"),
    }
    mentioned = {
        statistic
        for statistic, words in aliases.items()
        if any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in words)
    }
    if not mentioned:
        return None

    if any(word in lowered for word in ("only", "keep", "report just")):
        selected = mentioned
    elif any(word in lowered for word in ("remove", "drop", "exclude")):
        selected = set(current_statistics) - mentioned
    elif any(word in lowered for word in ("add", "include")):
        selected = set(current_statistics) | mentioned
    else:
        selected = mentioned
    return tuple(
        statistic for statistic in SUPPORTED_STATISTICS if statistic in selected
    )


def _decision_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "assistant_message",
            "research_question",
            "measurement_statistics",
            "unresolved_questions",
        ],
        "properties": {
            "assistant_message": {"type": "string", "minLength": 1},
            "research_question": {"type": "string", "minLength": 1},
            "measurement_statistics": {
                "type": "array",
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "enum": list(SUPPORTED_STATISTICS),
                },
            },
            "unresolved_questions": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
        },
    }


def _decision_from_payload(
    payload: Mapping[str, Any], provenance: Mapping[str, Any]
) -> DraftDecision:
    return DraftDecision(
        assistant_message=str(payload["assistant_message"]),
        research_question=str(payload["research_question"]),
        measurement_statistics=tuple(payload["measurement_statistics"]),
        unresolved_questions=tuple(payload["unresolved_questions"]),
        provenance=provenance,
    )
