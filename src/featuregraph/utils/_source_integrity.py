"""Verify downloaded source files against recorded fingerprints.

A study contract is fingerprinted, but until now the data it runs against was
not. A cached source file was reused whenever it existed and was non-empty,
which accepts a truncated or substituted download silently -- the same shape of
failure as filling in a missing column with an available one.

This module closes that gap. A manifest records the SHA-256 of each source file;
a file that does not match is refused rather than used. Files absent from the
manifest are not yet pinned and pass through unchanged, so a manifest can be
seeded incrementally without breaking existing callers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from featuregraph.studies.fingerprint import file_sha256


class SourceIntegrityError(RuntimeError):
    """Raised when a source file does not match its recorded fingerprint."""

    def __init__(
        self,
        path: Path,
        expected: str,
        actual: str,
        *,
        source: str | None = None,
    ) -> None:
        detail = f" downloaded from {source}" if source else ""
        super().__init__(
            f"Source file {path.name!r}{detail} does not match its recorded "
            f"fingerprint: expected={expected} actual={actual}. The cached copy "
            f"may be truncated or replaced; delete it and refresh, or update the "
            f"manifest deliberately if the upstream dataset was revised."
        )
        self.path = path
        self.expected = expected
        self.actual = actual


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Read a manifest, returning an empty one when the file is absent."""
    manifest_path = Path(path)
    if not manifest_path.is_file():
        return {"files": {}}
    try:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SourceIntegrityError(
            manifest_path, "a readable manifest", "unreadable"
        ) from error
    if not isinstance(loaded, dict):
        return {"files": {}}
    files = loaded.get("files")
    if not isinstance(files, dict):
        loaded["files"] = {}
    return loaded


def expected_fingerprint(manifest: dict[str, Any], filename: str) -> str | None:
    """The recorded SHA-256 for one file, or None when it is not pinned."""
    recorded = manifest.get("files", {}).get(filename)
    if isinstance(recorded, str) and recorded:
        return recorded
    if isinstance(recorded, dict):
        value = recorded.get("sha256")
        return value if isinstance(value, str) and value else None
    return None


def verify(
    path: Path,
    manifest: dict[str, Any],
    *,
    source: str | None = None,
) -> str | None:
    """Check one file against the manifest and return the fingerprint checked.

    Returns ``None`` when the file is not pinned, in which case nothing is
    verified and the caller proceeds as before.
    """
    expected = expected_fingerprint(manifest, path.name)
    if expected is None:
        return None
    actual = file_sha256(path)
    if actual != expected:
        raise SourceIntegrityError(path, expected, actual, source=source)
    return actual
