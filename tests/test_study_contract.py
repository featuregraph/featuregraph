import json

import pytest

from featuregraph import (
    StudyContractApprovalError,
    approve_study_contract,
    load_approved_study_contract,
    study_contract_differences,
    study_contract_payload,
    study_contract_sha256,
)


def _contract() -> dict[str, object]:
    contract: dict[str, object] = {
        "contract_version": "test-study-v1",
        "study": {"name": "test"},
    }
    contract["approval"] = {
        "status": "approved",
        "authority": "test researcher",
        "contract_sha256": study_contract_sha256(contract),
    }
    return contract


def test_load_approved_study_contract_verifies_fingerprint(tmp_path) -> None:
    path = tmp_path / "study_contract.json"
    contract = _contract()
    path.write_text(json.dumps(contract), encoding="utf-8")

    approved = load_approved_study_contract(path)

    assert approved.contract == contract
    assert approved.sha256 == contract["approval"]["contract_sha256"]
    assert approved.source_path == path.resolve()


def test_changed_contract_requires_new_approval(tmp_path) -> None:
    path = tmp_path / "study_contract.json"
    contract = _contract()
    contract["study"]["name"] = "changed after approval"
    path.write_text(json.dumps(contract), encoding="utf-8")

    with pytest.raises(StudyContractApprovalError, match="fingerprint"):
        load_approved_study_contract(path)


def test_unapproved_contract_cannot_execute(tmp_path) -> None:
    path = tmp_path / "study_contract.json"
    contract = _contract()
    contract["approval"]["status"] = "candidate"
    path.write_text(json.dumps(contract), encoding="utf-8")

    with pytest.raises(StudyContractApprovalError, match="status='approved'"):
        load_approved_study_contract(path)


def test_candidate_approval_is_explicit_and_does_not_mutate_payload() -> None:
    candidate = {
        "contract_version": "test-study-v1",
        "study": {"name": "test"},
        "unresolved_questions": [],
    }

    approved = approve_study_contract(
        candidate,
        authority="test researcher",
        validation_results={"schema": True, "evidence": True},
    )

    assert "approval" not in candidate
    assert study_contract_payload(approved) == candidate
    assert approved["approval"]["contract_sha256"] == study_contract_sha256(
        candidate
    )


def test_candidate_cannot_supply_its_own_approval() -> None:
    candidate = _contract()

    with pytest.raises(StudyContractApprovalError, match="may not contain"):
        approve_study_contract(
            candidate,
            authority="test researcher",
            validation_results={"schema": True},
        )


@pytest.mark.parametrize(
    ("candidate", "validations", "message"),
    [
        (
            {
                "contract_version": "test-study-v1",
                "unresolved_questions": ["Which boundary applies?"],
            },
            {"schema": True},
            "unresolved questions",
        ),
        (
            {
                "contract_version": "test-study-v1",
                "unresolved_questions": [],
            },
            {"schema": False},
            "failed checks",
        ),
        (
            {
                "contract_version": "test-study-v1",
                "unresolved_questions": [],
            },
            {},
            "requires explicit validation",
        ),
    ],
)
def test_candidate_must_pass_review_before_approval(
    candidate: dict[str, object],
    validations: dict[str, bool],
    message: str,
) -> None:
    with pytest.raises(StudyContractApprovalError, match=message):
        approve_study_contract(
            candidate,
            authority="test researcher",
            validation_results=validations,
        )


def test_study_contract_differences_are_leaf_level_and_ignore_approval() -> None:
    reference = _contract()
    candidate = study_contract_payload(reference)
    candidate["study"]["name"] = "candidate"
    candidate["measurements"] = ["mean"]

    differences = study_contract_differences(candidate, reference)

    assert differences == [
        {
            "path": "measurements",
            "candidate": ["mean"],
            "reference": "<missing>",
        },
        {
            "path": "study.name",
            "candidate": "candidate",
            "reference": "test",
        },
    ]
