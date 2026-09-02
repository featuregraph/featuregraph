"""Where downloaded source data lives, and whether fetching it is allowed.

Two loaders in this package reach the network on first use: BIDMC and
Tennessee Eastman. Both cached into a hardcoded path under the user's home
directory, which works on a laptop and does not work anywhere a deployment
actually runs. A container has no useful home directory, a read-only image
cannot create one, and an environment with no egress cannot fill it.

This module makes both answerable by configuration:

``FEATUREGRAPH_CACHE_DIR``
    Where cached source files live. Point it at a mounted volume that was
    seeded from a machine that *can* reach the source, and no download is
    needed. Unset, the behaviour is exactly as before.

``FEATUREGRAPH_OFFLINE``
    When set, a loader that would fetch raises ``SourceUnavailableError``
    instead. This is not a convenience: behind a blackhole route a request
    does not fail, it hangs until the timeout, once per file. Declaring the
    environment offline turns a sixty-second stall into an immediate answer
    that names what is missing and where to put it.

Nothing here weakens verification. A pre-seeded file is checked against the
recorded manifest exactly as a freshly downloaded one is, so seeding a cache
is a way to avoid a fetch, never a way to avoid the fingerprint.
"""

from __future__ import annotations

import os
from pathlib import Path

CACHE_DIR_VAR = "FEATUREGRAPH_CACHE_DIR"
OFFLINE_VAR = "FEATUREGRAPH_OFFLINE"

#: Values that mean "yes" in an environment variable. Anything else, including
#: the empty string, means no -- so `FEATUREGRAPH_OFFLINE=` does not silently
#: switch a deployment into offline mode.
_TRUE = frozenset({"1", "true", "yes", "on"})


class SourceUnavailableError(RuntimeError):
    """Raised when source data is absent and fetching it is not permitted.

    Distinct from ``SourceIntegrityError``: that one means the bytes are wrong,
    this one means there are no bytes. The remedies differ, so the exceptions
    do too.
    """

    def __init__(self, description: str, *, url: str, expected_at: Path) -> None:
        super().__init__(
            f"{description} is not present in the local cache and "
            f"{OFFLINE_VAR} is set, so it will not be downloaded. Seed the "
            f"cache by placing the file at {expected_at}, or point "
            f"{CACHE_DIR_VAR} at a directory that already holds it. The source "
            f"is {url}."
        )
        self.url = url
        self.expected_at = expected_at


def offline() -> bool:
    """Whether this environment forbids fetching source data."""
    return os.environ.get(OFFLINE_VAR, "").strip().lower() in _TRUE


def cache_root() -> Path:
    """The base directory for cached source data."""
    configured = os.environ.get(CACHE_DIR_VAR, "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "featuregraph"


def dataset_cache_path(*parts: str) -> Path:
    """Where a dataset's cache would be. Creates nothing, touches no disk.

    Asking whether data is present must not require permission to write. On a
    read-only mount, and before a cache exists at all, this is the only form of
    the question that can be answered.
    """
    return cache_root().joinpath(*parts)


def dataset_cache_dir(*parts: str) -> Path:
    """A per-dataset cache directory, created only when it does not exist.

    The existence check is not an optimisation. A pre-seeded volume may be
    mounted read-only, where an unconditional ``mkdir`` fails with EROFS even
    though the directory is already there and readable.
    """
    cache_dir = dataset_cache_path(*parts)
    if not cache_dir.is_dir():
        cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def require_fetch_allowed(description: str, *, url: str, expected_at: Path) -> None:
    """Refuse, with the remedy named, when this environment cannot fetch."""
    if offline():
        raise SourceUnavailableError(description, url=url, expected_at=expected_at)
