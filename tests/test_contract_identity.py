"""Fingerprint conventions across published study contracts.

Three states exist in the repository and each means something different:
an approved contract carries a named authority, a self-recorded one is
verifiable but unapproved, and an unfingerprinted one cannot be checked at all.
Conflating them is the hazard this module guards against.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from featuregraph.contracts import (
    StudyContractApprovalError,
    approve_study_contract,
    inspect_contract,
    verify_contract_integrity,
)
from featuregraph.studies.fingerprint import value_sha256

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts" / "studies"


def _self_recorded(**payload) -> dict:
    body = {"schema_version": "1.0", "execution_id": "demo-v1", **payload}
    return {**body, "contract_sha256": value_sha256(body)}


def _approved() -> dict:
    return approve_study_contract(
        {"contract_version": "v1", "unresolved_questions": [], "study": {"name": "x"}},
        authority="Nazia Habib",
        validation_results={"exclusive_states": True},
    )


# -- convention detection -------------------------------------------------


def test_detects_the_approval_convention() -> None:
    identity = inspect_contract(_approved())

    assert identity.convention == "approval"
    assert identity.consistent
    assert identity.carries_authority
    assert identity.authority == "Nazia Habib"


def test_detects_the_self_recorded_convention() -> None:
    identity = inspect_contract(_self_recorded())

    assert identity.convention == "self_recorded"
    assert identity.consistent
    # Verifiable, but nobody approved it, so it must not execute.
    assert not identity.carries_authority


def test_detects_an_unfingerprinted_contract() -> None:
    identity = inspect_contract({"schema_version": "1.0"})

    assert identity.convention == "unfingerprinted"
    assert identity.recorded is None
    assert not identity.consistent


# -- integrity ------------------------------------------------------------


def test_a_tampered_self_recorded_payload_is_inconsistent() -> None:
    contract = _self_recorded(window_samples=85)
    contract["window_samples"] = 86

    assert not inspect_contract(contract).consistent
    with pytest.raises(StudyContractApprovalError, match="self_recorded"):
        verify_contract_integrity(contract)


def test_a_tampered_approved_payload_is_inconsistent() -> None:
    contract = _approved()
    contract["study"] = {"name": "something else"}

    with pytest.raises(StudyContractApprovalError, match="approval"):
        verify_contract_integrity(contract)


def test_an_unfingerprinted_contract_cannot_be_verified() -> None:
    with pytest.raises(StudyContractApprovalError, match="records no fingerprint"):
        verify_contract_integrity({"schema_version": "1.0"})


def test_verification_returns_the_identity_on_success() -> None:
    identity = verify_contract_integrity(_self_recorded())

    assert identity.convention == "self_recorded"
    assert identity.consistent


def test_a_non_mapping_is_rejected() -> None:
    with pytest.raises(StudyContractApprovalError):
        inspect_contract("not a contract")


# -- the contracts actually published in this repository ------------------


@pytest.mark.parametrize(
    ("study", "convention", "has_authority"),
    [
        ("bidmc_window_85", "self_recorded", False),
        ("physionet_wearable", "approval", True),
        ("physionet_nori", "unfingerprinted", False),
    ],
)
def test_published_contracts_keep_their_conventions(
    study: str, convention: str, has_authority: bool
) -> None:
    """These fingerprints are cited publicly and must not be rewritten.

    The scientific API publishes bidmc_window_85's fingerprint, so changing it
    would invalidate a claim already made. Recognising each convention as it is
    keeps published records valid.
    """
    path = ARTIFACTS / study / "study_contract.json"
    if not path.is_file():
        pytest.skip(f"{path} is not present in this checkout")

    identity = inspect_contract(json.loads(path.read_text(encoding="utf-8")))

    assert identity.convention == convention
    assert identity.carries_authority is has_authority
    if convention != "unfingerprinted":
        assert identity.consistent, f"{study} no longer matches its own fingerprint"


def test_the_published_bidmc_fingerprint_is_the_one_the_api_serves() -> None:
    """Pins the exact value published at /api/v1/measurements/respiratory-period."""
    path = ARTIFACTS / "bidmc_window_85" / "study_contract.json"
    if not path.is_file():
        pytest.skip("bidmc_window_85 contract is not present in this checkout")

    identity = inspect_contract(json.loads(path.read_text(encoding="utf-8")))

    assert identity.recorded == (
        "621f654c6160d533f35e16b0e13f65350307b64855ebf4e12eb7d6159c14e8bb"
    )
    assert identity.consistent
