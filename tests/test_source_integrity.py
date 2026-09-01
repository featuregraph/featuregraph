"""Source-file integrity: a cached file is reused only if it still matches.

No test here touches the network. The download path is exercised by pointing the
loader's cache at a temporary directory and planting files in it.
"""

from __future__ import annotations

import pytest

from featuregraph.studies.fingerprint import file_sha256
from featuregraph.utils import _bidmc
from featuregraph.utils._source_integrity import (
    SourceIntegrityError,
    expected_fingerprint,
    load_manifest,
    verify,
)

CONTENT = b"Time [s], RESP\n0.000,1.0\n0.008,1.1\n"


@pytest.fixture()
def cached(tmp_path, monkeypatch):
    """A cache directory holding one real BIDMC-named file."""
    path = tmp_path / _bidmc.bidmc_filename(1, "Signals")
    path.write_bytes(CONTENT)
    monkeypatch.setattr(_bidmc, "get_cache_dir", lambda: tmp_path)
    return path


def test_absent_manifest_pins_nothing(tmp_path):
    manifest = load_manifest(tmp_path / "does-not-exist.json")

    assert manifest == {"files": {}}
    assert expected_fingerprint(manifest, "anything.csv") is None


def test_matching_file_passes_and_returns_its_digest(cached):
    digest = file_sha256(cached)

    assert verify(cached, {"files": {cached.name: digest}}) == digest


def test_unpinned_file_is_not_verified(cached):
    # Nothing recorded means nothing checked; behaviour is unchanged.
    assert verify(cached, {"files": {}}) is None


def test_truncated_file_is_refused(cached):
    digest = file_sha256(cached)
    cached.write_bytes(CONTENT[:10])  # non-empty, so a size check would pass

    with pytest.raises(SourceIntegrityError) as caught:
        verify(cached, {"files": {cached.name: digest}}, source="https://example/x.csv")

    assert caught.value.expected == digest
    assert caught.value.actual != digest
    assert "does not match its recorded fingerprint" in str(caught.value)


def test_substituted_file_is_refused(cached):
    digest = file_sha256(cached)
    cached.write_bytes(b"Time [s], RESP\n0.000,9.9\n0.008,9.9\n")

    with pytest.raises(SourceIntegrityError):
        verify(cached, {"files": {cached.name: digest}})


def test_manifest_accepts_either_a_string_or_a_record():
    plain = {"files": {"a.csv": "ab" * 32}}
    nested = {"files": {"a.csv": {"sha256": "ab" * 32, "bytes": 10}}}

    assert expected_fingerprint(plain, "a.csv") == "ab" * 32
    assert expected_fingerprint(nested, "a.csv") == "ab" * 32
    assert expected_fingerprint({"files": {"a.csv": ""}}, "a.csv") is None


# -- the loader path, without network ------------------------------------


def test_cached_download_is_reused_when_it_matches(cached, monkeypatch):
    monkeypatch.setattr(
        _bidmc, "bidmc_manifest", lambda: {"files": {cached.name: file_sha256(cached)}}
    )

    returned = _bidmc.download_bidmc_file(1, "Signals")

    assert returned == cached
    assert returned.read_bytes() == CONTENT


def test_cached_download_is_refused_when_it_does_not_match(cached, monkeypatch):
    # This is the case a size check accepted: non-empty, cached, and wrong.
    monkeypatch.setattr(
        _bidmc, "bidmc_manifest", lambda: {"files": {cached.name: "00" * 32}}
    )

    with pytest.raises(SourceIntegrityError):
        _bidmc.download_bidmc_file(1, "Signals")


def test_an_unpinned_cached_file_still_loads(cached, monkeypatch):
    # Before a manifest is seeded, nothing changes for existing callers.
    monkeypatch.setattr(_bidmc, "bidmc_manifest", lambda: {"files": {}})

    assert _bidmc.download_bidmc_file(1, "Signals") == cached


def test_shipped_manifest_is_well_formed():
    # It ships empty until seeded from an environment that can reach PhysioNet,
    # but it must always parse and expose a files mapping.
    manifest = load_manifest(_bidmc.BIDMC_MANIFEST_PATH)

    assert isinstance(manifest.get("files"), dict)
    assert manifest.get("version") == _bidmc.BIDMC_VERSION


def test_source_fingerprint_lookup_is_none_until_pinned(monkeypatch):
    monkeypatch.setattr(_bidmc, "bidmc_manifest", lambda: {"files": {}})

    assert _bidmc.bidmc_source_fingerprint(1, "Signals") is None

    name = _bidmc.bidmc_filename(2, "Signals")
    monkeypatch.setattr(_bidmc, "bidmc_manifest", lambda: {"files": {name: "cd" * 32}})
    assert _bidmc.bidmc_source_fingerprint(2, "Signals") == "cd" * 32
