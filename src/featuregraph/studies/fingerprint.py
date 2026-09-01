"""Deterministic serialization and hashing for study artifacts.

Contracts, parameter dictionaries, and other declarative study values are
fingerprinted so a rerun can be checked against a recorded result. This is a
generic counterpart to ``featuregraph.contracts.study_contract``, which
fingerprints one specific contract shape; these helpers fingerprint any JSON-
serializable value a study runner wants to record or compare.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> str:
    """Serialize a value deterministically for storage, diffing, and hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def value_sha256(value: Any) -> str:
    """Fingerprint a JSON-serializable value from its canonical serialization."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    """Fingerprint a file's exact bytes, for provenance over notebooks and inputs."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
