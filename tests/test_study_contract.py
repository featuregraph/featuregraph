import json

import pytest

from featuregraph import (
    StudyContractApprovalError,
    load_approved_study_contract,
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
