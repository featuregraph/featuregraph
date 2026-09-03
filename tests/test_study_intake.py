"""The intake is a study contract with holes, and the holes are derived."""

from __future__ import annotations

import pandas as pd
import pytest

from featuregraph.contracts import (
    StudyContractApprovalError,
    approve_study_contract,
    compile_states,
)
from featuregraph.study_builder.intake import (
    APPROVABLE,
    COMPILABLE,
    FIELDS,
    INTAKE_SCHEMA_VERSION,
    IntakeIncompleteError,
    StudyIntake,
    StudyIntakeError,
    render_checkpoint,
)

# The payload the deployed v1 assistant emits for a session where nothing has
# been declared yet. Kept verbatim so a real checkpoint stays loadable.
V1_EMPTY_CHECKPOINT = {
    "schema_version": 1,
    "status": "intake_in_progress",
    "executor_registered": False,
    "title": "Not yet specified",
    "research_question": "Not yet specified",
    "data_source": "Not yet specified",
    "observation_schema": [],
    "grouping_and_order": "Not yet specified",
    "time_semantics": "Not yet specified",
    "states_or_labels": [],
    "preprocessing_steps": [],
    "operator_parameters": [],
    "boundary_rules": [],
    "completeness_rules": [],
    "object_definition": "Not yet specified",
    "measurements": [],
    "validations": [],
    "provenance": [],
    "exclusions": [],
    "claim_limits": [],
    "missing_information": [
        "boundary_rules",
        "claim_limits",
        "completeness_rules",
        "data_source",
        "exclusions",
        "grouping_and_order",
        "measurements",
        "object_definition",
        "observation_schema",
        "operator_parameters",
        "preprocessing_steps",
        "provenance",
        "research_question",
        "states_or_labels",
        "time_semantics",
        "title",
        "validations",
    ],
}

COMPILABLE_DECLARATIONS = {
    "observation_schema": [
        {"column": "series_id", "dtype": "string"},
        {"column": "t", "dtype": "int64", "unit": "seconds"},
        {"column": "level", "dtype": "float64", "unit": "litres"},
    ],
    "grouping_and_order": {"group_by": ["series_id"], "order_by": "t"},
    "states_or_labels": [
        {
            "name": "filling",
            "when": {
                "op": "gt",
                "left": {"column": "level"},
                "right": {"parameter": "threshold"},
            },
        },
        {
            "name": "draining",
            "when": {
                "op": "le",
                "left": {"column": "level"},
                "right": {"parameter": "threshold"},
            },
        },
    ],
    "operator_parameters": [{"name": "threshold", "value": 5.0}],
    "boundary_rules": {"include_first_entry": True, "include_last_exit": True},
    "completeness_rules": {"exclusive": True, "exhaustive": True},
}

APPROVABLE_DECLARATIONS = {
    "title": "Tank fill regime",
    "research_question": "Does the tank spend longer filling than draining?",
    "data_source": "synthetic fixture, tank_fill_v1",
    "time_semantics": "Each row is an instantaneous reading at time t.",
    "preprocessing_steps": [],
    "object_definition": "One row per contiguous run of a single regime.",
    "measurements": ["mean duration per regime"],
    "validations": ["states are exclusive", "states are exhaustive"],
    "provenance": ["contract sha256", "fixture sha256"],
    "exclusions": [],
    "claim_limits": ["Descriptive only; no causal claim about the pump."],
}


def complete_intake() -> StudyIntake:
    return StudyIntake.empty().declare(
        **COMPILABLE_DECLARATIONS, **APPROVABLE_DECLARATIONS
    )


def observations() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "series_id": ["a"] * 6,
            "t": [0, 1, 2, 3, 4, 5],
            "level": [1.0, 4.0, 6.0, 9.0, 7.0, 2.0],
        }
    )


def test_v1_checkpoint_round_trips_as_entirely_unset():
    intake = StudyIntake.from_payload(V1_EMPTY_CHECKPOINT)

    assert (
        list(intake.missing_information) == V1_EMPTY_CHECKPOINT["missing_information"]
    )
    assert intake.status == V1_EMPTY_CHECKPOINT["status"]
    assert intake.executor_registered is False


def test_every_declared_field_is_covered_by_a_tier():
    tiers = {field.tier for field in FIELDS}

    assert tiers == {COMPILABLE, APPROVABLE}
    assert len(FIELDS) == len(V1_EMPTY_CHECKPOINT["missing_information"])


def test_missing_information_is_derived_not_stored():
    intake = StudyIntake.empty().declare(title="Tank fill regime")

    assert "title" not in intake.missing_information
    # A payload cannot assert its own completeness: the loader ignores whatever
    # missing_information it carried and recomputes it.
    reloaded = StudyIntake.from_payload(
        {**intake.to_payload(), "missing_information": []}
    )
    assert reloaded.missing_information == intake.missing_information


def test_an_empty_list_is_an_answer_from_v2_on():
    intake = StudyIntake.empty().declare(preprocessing_steps=[])

    assert "preprocessing_steps" not in intake.missing_information
    assert intake.get("preprocessing_steps") == []
    # v1 wrote [] for "unanswered", so the same value must still read as unset
    # when the payload says it is v1.
    legacy = StudyIntake.from_payload({"schema_version": 1, "preprocessing_steps": []})
    assert "preprocessing_steps" in legacy.missing_information


def test_retracting_a_field_makes_it_missing_again():
    intake = complete_intake().declare(research_question=None)

    assert "research_question" in intake.missing_information
    assert not intake.is_approvable


def test_prose_where_a_rule_is_needed_is_neither_missing_nor_compilable():
    intake = complete_intake().declare(completeness_rules=["states should not overlap"])

    assert "completeness_rules" not in intake.missing_information
    assert intake.unstructured == ("completeness_rules",)
    assert not intake.is_compilable

    with pytest.raises(IntakeIncompleteError) as error:
        intake.to_state_contract()
    assert error.value.unstructured == ("completeness_rules",)
    assert error.value.unset == ()


def test_compilable_and_approvable_are_tracked_separately():
    partial = StudyIntake.empty().declare(**COMPILABLE_DECLARATIONS)

    assert partial.is_compilable
    assert not partial.is_approvable
    assert partial.missing_in_tier(COMPILABLE) == ()
    assert set(partial.missing_in_tier(APPROVABLE)) == set(APPROVABLE_DECLARATIONS)


def test_emitted_contract_compiles_against_real_observations():
    contract = complete_intake().to_state_contract()

    assert contract["version"] == "state-contract-v1"
    result = compile_states(observations(), contract)

    assert set(result.observations["state"]) == {"filling", "draining"}
    assert result.validation_report["passed"].all()


def test_a_column_the_schema_never_declared_is_refused_before_any_data():
    intake = complete_intake().declare(
        grouping_and_order={"group_by": ["subject_id"], "order_by": "t"}
    )

    with pytest.raises(IntakeIncompleteError, match="subject_id"):
        intake.to_state_contract()


def test_a_parameter_used_without_a_value_is_refused():
    intake = complete_intake().declare(operator_parameters=[])

    with pytest.raises(IntakeIncompleteError, match="threshold"):
        intake.to_state_contract()


def test_supplied_labels_are_an_alternative_to_declared_states():
    intake = complete_intake().declare(
        observation_schema=[
            {"column": "series_id"},
            {"column": "t"},
            {"column": "phase"},
        ],
        states_or_labels={"state_column": "phase"},
        operator_parameters=[],
    )
    contract = intake.to_state_contract()

    assert contract["state_column"] == "phase"
    assert "states" not in contract


def test_holes_become_unresolved_questions_and_block_approval():
    candidate = (
        StudyIntake.empty().declare(title="Tank fill regime").to_study_candidate()
    )

    assert candidate["unresolved_questions"]
    assert "state_contract" not in candidate
    with pytest.raises(StudyContractApprovalError, match="unresolved questions"):
        approve_study_contract(
            candidate, authority="Nazia Habib", validation_results={"reviewed": True}
        )


def test_a_complete_intake_approves_under_the_existing_gate():
    candidate = complete_intake().to_study_candidate()

    assert candidate["unresolved_questions"] == []
    approved = approve_study_contract(
        candidate, authority="Nazia Habib", validation_results={"reviewed": True}
    )

    assert approved["approval"]["authority"] == "Nazia Habib"
    assert len(approved["approval"]["contract_sha256"]) == 64
    # The contract the researcher approved is the one the compiler will run.
    compile_states(observations(), approved["state_contract"])


def test_the_candidate_never_grants_itself_approval():
    assert "approval" not in complete_intake().to_study_candidate()


def test_payload_round_trips_through_v2():
    intake = complete_intake()

    assert StudyIntake.from_payload(intake.to_payload()).to_payload() == (
        intake.to_payload()
    )
    assert intake.to_payload()["schema_version"] == INTAKE_SCHEMA_VERSION


def test_unknown_fields_are_refused_rather_than_dropped():
    with pytest.raises(StudyIntakeError, match="sample_rate"):
        StudyIntake.from_payload({"schema_version": 2, "sample_rate": 125})
    with pytest.raises(StudyIntakeError, match="sample_rate"):
        StudyIntake.empty().declare(sample_rate=125)


def test_checkpoint_is_rendered_from_the_intake():
    empty = render_checkpoint(StudyIntake.from_payload(V1_EMPTY_CHECKPOINT))

    assert "Untitled study" in empty
    assert "Status: **intake in progress**" in empty
    assert "- Research question: not yet specified" in empty
    assert "Compiles today: no" in empty

    done = render_checkpoint(complete_intake())
    assert "Status: **awaiting approval**" in done
    assert "Compiles today: yes" in done
    assert "Approvable today: yes" in done
    assert "- Preprocessing steps: declared as none" in done


def test_a_constructed_timeline_is_an_ordering():
    intake = StudyIntake.empty().declare(
        **{
            **COMPILABLE_DECLARATIONS,
            "grouping_and_order": {
                "group_by": ["series_id"],
                "timeline": {"frequency": "1s", "closure": "left"},
            },
        }
    )

    # Placing observations on a regular timeline fixes their order at least as
    # firmly as naming a sort column, and names no column at all. Demanding
    # 'order_by' reported that choice as an omission.
    assert intake.unstructured == ()
    assert intake.to_state_contract()["group_by"] == ["series_id"]


def test_an_ordering_declares_one_thing_or_the_other():
    intake = StudyIntake.empty().declare(
        **{**COMPILABLE_DECLARATIONS, "grouping_and_order": {"group_by": ["series_id"]}}
    )

    assert intake.unstructured == ("grouping_and_order",)


def test_reader_reports_a_v2_derivation_as_preprocessing():
    """A derivation the contract carries is preprocessing the fingerprint covers."""
    from featuregraph.study_builder.intake import intake_from_study_contract

    contract = {
        "contract_version": "study-contract-v1",
        "study": {"name": "envelope", "unit_of_analysis": "occurrence"},
        "state_compiler": {
            "version": "state-contract-v2",
            "missing_policy": "exclude",
            "parameters": {"window": 100, "atol": 1e-12},
            "derive": {
                "smooth": {
                    "op": "shift",
                    "value": {
                        "op": "rolling_max",
                        "value": {"column": "respiration"},
                        "window": {"parameter": "window"},
                    },
                    "periods": {"op": "neg", "value": {"parameter": "window"}},
                },
                "change": {"op": "diff", "value": {"column": "smooth"}},
            },
            "states": {
                "rising": {
                    "op": "gt",
                    "left": {"column": "change"},
                    "right": {"parameter": "atol"},
                }
            },
        },
    }

    intake = intake_from_study_contract(contract)

    assert intake.values["preprocessing_steps"] == [
        "smooth = shift(rolling_max(respiration, window=window), periods=-window)",
        "change = diff(smooth)",
        "observations a derivation leaves undefined are excluded from the "
        "partition and counted in the validation report",
    ]
