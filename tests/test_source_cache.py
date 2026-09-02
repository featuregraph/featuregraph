"""Where cached source data lives, and when fetching it is allowed.

Two loaders in this package download on first use. Both cached to a hardcoded
path under the user's home directory, which is unreachable configuration for
anything running in a container and unusable in an environment with no egress.

No test here touches the network. The offline tests would fail loudly if one
did, because a request is exactly what they assert does not happen.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from featuregraph.utils import _bidmc, _eastman
from featuregraph.utils._cache import (
    CACHE_DIR_VAR,
    OFFLINE_VAR,
    SourceUnavailableError,
    cache_root,
    dataset_cache_dir,
    offline,
)
from featuregraph.utils._source_integrity import SourceIntegrityError

CONTENT = b"Time [s], RESP\n0.000,1.0\n0.008,1.1\n"


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Neither variable is set unless a test sets it."""
    monkeypatch.delenv(CACHE_DIR_VAR, raising=False)
    monkeypatch.delenv(OFFLINE_VAR, raising=False)


# -- where the cache lives ------------------------------------------------


def test_the_default_location_is_unchanged() -> None:
    assert cache_root() == Path.home() / ".cache" / "featuregraph"


def test_the_location_is_configurable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(CACHE_DIR_VAR, str(tmp_path / "mounted"))

    assert cache_root() == tmp_path / "mounted"


def test_a_configured_location_expands_a_home_shortcut(monkeypatch) -> None:
    monkeypatch.setenv(CACHE_DIR_VAR, "~/somewhere")

    assert cache_root() == Path.home() / "somewhere"


def test_an_empty_setting_falls_back_to_the_default(monkeypatch) -> None:
    # An unset variable and a variable set to nothing must mean the same thing.
    monkeypatch.setenv(CACHE_DIR_VAR, "   ")

    assert cache_root() == Path.home() / ".cache" / "featuregraph"


def test_both_loaders_follow_the_setting(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(CACHE_DIR_VAR, str(tmp_path))

    assert _bidmc.get_cache_dir() == tmp_path / "bidmc" / _bidmc.BIDMC_VERSION
    assert _eastman.get_tep_cache_dir() == tmp_path / "tennessee_eastman"


def test_a_cache_directory_is_created_when_absent(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(CACHE_DIR_VAR, str(tmp_path / "fresh"))

    created = dataset_cache_dir("bidmc", "1.0.0")

    assert created.is_dir()


def test_an_existing_directory_is_not_recreated(monkeypatch, tmp_path) -> None:
    """A seeded volume may be mounted read-only, where mkdir fails with EROFS.

    The directory is already there and readable, so the call must not try.
    """
    monkeypatch.setenv(CACHE_DIR_VAR, str(tmp_path))
    (tmp_path / "bidmc" / "1.0.0").mkdir(parents=True)

    def refuse(*args, **kwargs):
        raise OSError("Read-only file system")

    monkeypatch.setattr(Path, "mkdir", refuse)

    assert dataset_cache_dir("bidmc", "1.0.0") == tmp_path / "bidmc" / "1.0.0"


# -- whether fetching is allowed ------------------------------------------


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " on "])
def test_offline_is_recognised(monkeypatch, value: str) -> None:
    monkeypatch.setenv(OFFLINE_VAR, value)

    assert offline() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "maybe"])
def test_anything_else_means_online(monkeypatch, value: str) -> None:
    # Notably the empty string: exporting the variable with no value must not
    # silently switch a deployment into offline mode.
    monkeypatch.setenv(OFFLINE_VAR, value)

    assert offline() is False


# -- the loader, offline --------------------------------------------------


@pytest.fixture()
def cache(monkeypatch, tmp_path) -> Path:
    monkeypatch.setenv(CACHE_DIR_VAR, str(tmp_path))
    return tmp_path / "bidmc" / _bidmc.BIDMC_VERSION


def test_an_absent_file_offline_names_the_remedy(monkeypatch, cache) -> None:
    monkeypatch.setenv(OFFLINE_VAR, "1")

    with pytest.raises(SourceUnavailableError) as caught:
        _bidmc.download_bidmc_file(1, "Signals")

    message = str(caught.value)
    assert "bidmc_01_Signals.csv" in message
    assert str(cache / "bidmc_01_Signals.csv") in message
    assert CACHE_DIR_VAR in message
    assert "physionet.org" in message


def test_a_seeded_file_loads_offline(monkeypatch, cache) -> None:
    """The whole point: seed the cache and no network is needed."""
    cache.mkdir(parents=True)
    seeded = cache / _bidmc.bidmc_filename(1, "Signals")
    seeded.write_bytes(CONTENT)
    monkeypatch.setenv(OFFLINE_VAR, "1")
    monkeypatch.setattr(_bidmc, "bidmc_manifest", lambda: {"files": {}})

    assert _bidmc.download_bidmc_file(1, "Signals") == seeded


def test_seeding_is_not_a_way_around_the_fingerprint(monkeypatch, cache) -> None:
    """A seeded file is verified exactly as a downloaded one is.

    Otherwise pre-seeding would be a hole in the integrity guarantee rather
    than a way to avoid a fetch.
    """
    cache.mkdir(parents=True)
    (cache / _bidmc.bidmc_filename(1, "Signals")).write_bytes(CONTENT)
    monkeypatch.setenv(OFFLINE_VAR, "1")
    monkeypatch.setattr(
        _bidmc,
        "bidmc_manifest",
        lambda: {"files": {_bidmc.bidmc_filename(1, "Signals"): "00" * 32}},
    )

    with pytest.raises(SourceIntegrityError):
        _bidmc.download_bidmc_file(1, "Signals")


# -- asking before trying -------------------------------------------------


def test_availability_is_answerable_without_fetching(monkeypatch, cache) -> None:
    assert _bidmc.is_bidmc_file_cached(1, "Signals") is False
    # The probe created nothing on the way to that answer.
    assert not cache.exists()

    cache.mkdir(parents=True)
    (cache / _bidmc.bidmc_filename(1, "Signals")).write_bytes(CONTENT)

    assert _bidmc.is_bidmc_file_cached(1, "Signals") is True


def test_availability_is_answerable_on_a_read_only_mount(monkeypatch, cache) -> None:
    """No cache directory, no write permission, and still a usable answer."""

    def refuse(*args, **kwargs):
        raise OSError("Read-only file system")

    monkeypatch.setattr(Path, "mkdir", refuse)

    assert _bidmc.is_bidmc_file_cached(1, "Signals") is False


def test_an_empty_file_does_not_count_as_cached(monkeypatch, cache) -> None:
    # A zero-byte file is what a failed download leaves behind.
    cache.mkdir(parents=True)
    (cache / _bidmc.bidmc_filename(1, "Signals")).write_bytes(b"")

    assert _bidmc.is_bidmc_file_cached(1, "Signals") is False
