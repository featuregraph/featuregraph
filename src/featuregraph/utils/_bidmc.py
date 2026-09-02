from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd
import requests

from featuregraph.utils._cache import (
    dataset_cache_dir,
    dataset_cache_path,
    require_fetch_allowed,
)
from featuregraph.utils._source_integrity import load_manifest, verify

BIDMC_VERSION = "1.0.0"
BIDMC_BASE_URL = (
    f"https://physionet.org/files/bidmc/{BIDMC_VERSION}/bidmc_csv"
)

FileKind = Literal["Signals", "Numerics", "Breaths", "Fix"]

#: Recorded SHA-256 of each pinned source file. Seed or refresh it with
#: ``python -m scripts.record_bidmc_manifest``. Files absent from it are not
#: yet pinned and are used unverified.
BIDMC_MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent / "datasets" / "bidmc_manifest.json"
)


def bidmc_manifest() -> dict:
    """The recorded source fingerprints for this BIDMC version."""
    return load_manifest(BIDMC_MANIFEST_PATH)


def bidmc_source_fingerprint(subject: int, kind: FileKind) -> str | None:
    """The recorded fingerprint for one source file, or None if unpinned.

    A study runner records this alongside its contract fingerprint, so a result
    is identified by both the rules applied and the bytes they were applied to.
    """
    from featuregraph.utils._source_integrity import expected_fingerprint

    return expected_fingerprint(bidmc_manifest(), bidmc_filename(subject, kind))


def get_cache_dir() -> Path:
    """
    Return the BIDMC cache directory outside the Git repository.

    Honours ``FEATUREGRAPH_CACHE_DIR`` so a deployment can point this at a
    mounted volume seeded from a machine that can reach PhysioNet.
    """
    return dataset_cache_dir("bidmc", BIDMC_VERSION)


def is_bidmc_file_cached(subject: int, kind: FileKind) -> bool:
    """Whether one source file is already present locally. Never fetches.

    Answers "will resolving this need the network", which is what a caller
    needs before deciding to try. It deliberately does not verify: hashing is
    the loader's job at the point of use, and an availability probe that reads
    every byte of 53 files is not a probe.
    """
    # dataset_cache_path, not get_cache_dir: a probe must not create anything,
    # and on a read-only mount with no cache yet, creating is not possible.
    path = dataset_cache_path("bidmc", BIDMC_VERSION) / bidmc_filename(subject, kind)
    return path.is_file() and path.stat().st_size > 0


def bidmc_filename(subject: int, kind: FileKind) -> str:
    """
    Return the source filename for a BIDMC subject file.
    """
    if not isinstance(subject, int):
        raise TypeError("subject must be an integer")

    if not 1 <= subject <= 53:
        raise ValueError("subject must be between 1 and 53")

    suffix = "txt" if kind == "Fix" else "csv"
    return f"bidmc_{subject:02d}_{kind}.{suffix}"


def download_bidmc_file(
    subject: int,
    kind: FileKind,
    *,
    refresh: bool = False,
    timeout: int = 60,
) -> Path:
    """
    Download one BIDMC source file into the external cache.
    """
    filename = bidmc_filename(subject, kind)
    destination = get_cache_dir() / filename

    url = f"{BIDMC_BASE_URL}/{filename}"

    # A cached file is reused only if it still matches its recorded
    # fingerprint. Size alone accepts a truncated or substituted download.
    if destination.exists() and destination.stat().st_size > 0 and not refresh:
        verify(destination, bidmc_manifest(), source=url)
        return destination

    # Nothing is cached and a fetch is about to happen. In an environment
    # declared offline, say so now: behind a blackhole route the request below
    # does not fail, it hangs for the full timeout, once per file.
    require_fetch_allowed(
        f"BIDMC file {filename!r}",
        url=url,
        expected_at=destination,
    )

    temporary_path = destination.with_suffix(
        destination.suffix + ".part"
    )

    try:
        with requests.get(
            url,
            stream=True,
            timeout=timeout,
        ) as response:
            response.raise_for_status()

            with temporary_path.open("wb") as file:
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        file.write(chunk)

        if temporary_path.stat().st_size == 0:
            raise RuntimeError(
                f"Downloaded BIDMC file is empty: {url}"
            )

        temporary_path.replace(destination)
        # Verify what actually landed, not what was requested.
        verify(destination, bidmc_manifest(), source=url)

    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return destination


def _load_bidmc_csv(
    subject: int,
    kind: Literal["Signals", "Numerics", "Breaths"],
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Download and load one BIDMC CSV table.
    """
    path = download_bidmc_file(
        subject,
        kind,
        refresh=refresh,
    )

    df = pd.read_csv(path)

    # Clean source-column whitespace at the loader boundary.
    df.columns = df.columns.str.strip()

    # Ensure the observation table identifies its source subject.
    df["subject"] = subject

    df.attrs["bidmc_subject"] = subject
    df.attrs["bidmc_kind"] = kind
    df.attrs["source_file"] = str(path)
    df.attrs["bidmc_version"] = BIDMC_VERSION

    return df


def load_bidmc_signals(
    subject: int,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Load waveform observations for one BIDMC subject.
    """
    return _load_bidmc_csv(
        subject,
        "Signals",
        refresh=refresh,
    )


def load_bidmc_numerics(
    subject: int,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Load numeric observations for one BIDMC subject.
    """
    return _load_bidmc_csv(
        subject,
        "Numerics",
        refresh=refresh,
    )


def load_bidmc_breaths(
    subject: int,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Load breath annotations for one BIDMC subject.
    """
    return _load_bidmc_csv(
        subject,
        "Breaths",
        refresh=refresh,
    )


def load_bidmc_subject(
    subject: int,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Load the waveform observation table for one BIDMC subject.

    This is the primary BIDMC loader used by FeatureGraph. It returns a
    DataFrame directly so that its output can be passed into behavioral
    constructors such as ``featuregraph.oscillate``.

    Numerics and breath annotations remain available through
    ``load_bidmc_numerics`` and ``load_bidmc_breaths``.

    Parameters
    ----------
    subject:
        BIDMC subject number, between 1 and 53.

    refresh:
        Redownload the source waveform file even when it is cached.

    Returns
    -------
    pandas.DataFrame
        Waveform observations for one subject.
    """
    return load_bidmc_signals(
        subject,
        refresh=refresh,
    )


def clear_bidmc_cache() -> None:
    """
    Remove locally cached BIDMC files.
    """
    cache_dir = get_cache_dir()

    for path in cache_dir.iterdir():
        if path.is_file():
            path.unlink()