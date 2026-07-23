from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd
import requests


BIDMC_VERSION = "1.0.0"
BIDMC_BASE_URL = (
    f"https://physionet.org/files/bidmc/{BIDMC_VERSION}/bidmc_csv"
)

FileKind = Literal["Signals", "Numerics", "Breaths", "Fix"]


def get_cache_dir() -> Path:
    """
    Return the BIDMC cache directory outside the Git repository.
    """
    cache_dir = (
        Path.home()
        / ".cache"
        / "featuregraph"
        / "bidmc"
        / BIDMC_VERSION
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


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

    if destination.exists() and destination.stat().st_size > 0 and not refresh:
        return destination

    url = f"{BIDMC_BASE_URL}/{filename}"
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