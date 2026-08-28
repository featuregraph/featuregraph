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


def study_contract_payload(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Return the researcher-controlled payload without approval metadata."""

    if not isinstance(contract, Mapping):
        raise StudyContractApprovalError("A study contract must be a mapping.")
    payload = deepcopy(dict(contract))
    payload.pop("approval", None)
    return payload


def canonical_study_contract(contract: Mapping[str, Any]) -> str:
    """Return the canonical JSON covered by researcher approval.

    The ``approval`` record is excluded because it stores the fingerprint of
    the remaining contract and would otherwise make the hash self-referential.
    """

    payload = study_contract_payload(contract)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def study_contract_sha256(contract: Mapping[str, Any]) -> str:
    """Fingerprint every contract field except its approval record."""

    canonical = canonical_study_contract(contract)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def study_contract_differences(
    candidate: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return deterministic leaf-level differences between two payloads."""

    left = study_contract_payload(candidate)
    right = study_contract_payload(reference)
    differences: list[dict[str, Any]] = []

    def compare(path: str, candidate_value: Any, reference_value: Any) -> None:
        if isinstance(candidate_value, Mapping) and isinstance(
            reference_value, Mapping
        ):
            for key in sorted(set(candidate_value) | set(reference_value)):
                child = f"{path}.{key}" if path else str(key)
                compare(
                    child,
                    candidate_value.get(key, "<missing>"),
                    reference_value.get(key, "<missing>"),
                )
            return
        if isinstance(candidate_value, list) and isinstance(reference_value, list):
            for index in range(max(len(candidate_value), len(reference_value))):
                child = f"{path}[{index}]"
                compare(
                    child,
                    candidate_value[index]
                    if index < len(candidate_value)
                    else "<missing>",
                    reference_value[index]
                    if index < len(reference_value)
                    else "<missing>",
                )
            return
        if candidate_value != reference_value:
            differences.append(
                {
                    "path": path,
                    "candidate": deepcopy(candidate_value),
                    "reference": deepcopy(reference_value),
                }
            )

    compare("", left, right)
    return differences


def approve_study_contract(
    candidate: Mapping[str, Any],
    *,
    authority: str,
    validation_results: Mapping[str, bool],
) -> dict[str, Any]:
    """Create an approved contract after explicit deterministic checks.

    The candidate must be an approval-free payload. This prevents a model or
    other authoring helper from granting itself execution authority.
    """

    if not isinstance(candidate, Mapping):
        raise StudyContractApprovalError("A study candidate must be a mapping.")
    if "approval" in candidate:
        raise StudyContractApprovalError(
            "A study candidate may not contain approval metadata."
        )
    if not isinstance(authority, str) or not authority.strip():
        raise StudyContractApprovalError(
            "Study approval must identify a non-empty authority."
        )
    if not validation_results:
        raise StudyContractApprovalError(
            "Study approval requires explicit validation results."
        )
    failed = sorted(
        name for name, passed in validation_results.items() if passed is not True
    )
    if failed:
        raise StudyContractApprovalError(
            "A study candidate with failed checks cannot be approved: "
            + ", ".join(failed)
        )
    unresolved = candidate.get("unresolved_questions", [])
    if not isinstance(unresolved, list) or unresolved:
        raise StudyContractApprovalError(
            "A study candidate with unresolved questions cannot be approved."
        )

    approved = deepcopy(dict(candidate))
    approved["approval"] = {
        "status": "approved",
        "authority": authority.strip(),
        "contract_sha256": study_contract_sha256(approved),
    }
    return approved


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
