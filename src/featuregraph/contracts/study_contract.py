"""Load researcher-approved study contracts with deterministic fingerprints."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class StudyContractApprovalError(ValueError):
    """Raised when a study contract is missing or has invalid approval evidence."""


@dataclass(frozen=True)
class ApprovedStudyContract:
    """An immutable approval result for one loaded study-contract payload."""

    contract: dict[str, Any]
    sha256: str
    source_path: Path


def canonical_study_contract(contract: Mapping[str, Any]) -> str:
    """Return the canonical JSON covered by researcher approval.

    The ``approval`` record is excluded because it stores the fingerprint of
    the remaining contract and would otherwise make the hash self-referential.
    """

    if not isinstance(contract, Mapping):
        raise StudyContractApprovalError("A study contract must be a mapping.")
    payload = deepcopy(dict(contract))
    payload.pop("approval", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def study_contract_sha256(contract: Mapping[str, Any]) -> str:
    """Fingerprint every contract field except its approval record."""

    canonical = canonical_study_contract(contract)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_approved_study_contract(path: str | Path) -> ApprovedStudyContract:
    """Load a JSON contract only when its approval fingerprint is exact."""

    source_path = Path(path).resolve()
    try:
        contract = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StudyContractApprovalError(
            f"Could not load study contract at {source_path}: {error}"
        ) from error

    if not isinstance(contract, dict):
        raise StudyContractApprovalError("A study contract must be a JSON object.")
    version = contract.get("contract_version")
    if not isinstance(version, str) or not version:
        raise StudyContractApprovalError(
            "A study contract must declare a non-empty 'contract_version'."
        )

    approval = contract.get("approval")
    if not isinstance(approval, dict):
        raise StudyContractApprovalError(
            "A study contract must contain an 'approval' object."
        )
    if approval.get("status") != "approved":
        raise StudyContractApprovalError(
            "Study execution requires approval.status='approved'."
        )
    authority = approval.get("authority")
    if not isinstance(authority, str) or not authority.strip():
        raise StudyContractApprovalError(
            "Study approval must identify a non-empty authority."
        )

    expected = approval.get("contract_sha256")
    actual = study_contract_sha256(contract)
    if expected != actual:
        raise StudyContractApprovalError(
            "Study contract fingerprint does not match its approval record: "
            f"expected={expected!r} actual={actual!r}."
        )

    return ApprovedStudyContract(
        contract=deepcopy(contract),
        sha256=actual,
        source_path=source_path,
    )
