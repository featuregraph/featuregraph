from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

import pandas as pd
import requests

CAPNOBASE_DOI = "doi:10.5683/SP2/NLB8IT"
CAPNOBASE_VERSION = "1.1"
CAPNOBASE_API_URL = "https://borealisdata.ca/api"
CAPNOBASE_SAMPLING_RATE = 300

CAPNOBASE_CASES = (
    "0009",
    "0015",
    "0016",
    "0018",
    "0023",
    "0028",
    "0029",
    "0030",
    "0031",
    "0032",
    "0035",
    "0038",
    "0103",
    "0104",
    "0105",
    "0115",
    "0121",
    "0122",
    "0123",
    "0125",
    "0127",
    "0128",
    "0133",
    "0134",
    "0142",
    "0147",
    "0148",
    "0149",
    "0150",
    "0309",
    "0311",
    "0312",
    "0313",
    "0322",
    "0325",
    "0328",
    "0329",
    "0330",
    "0331",
    "0332",
    "0333",
    "0370",
)

FileKind = Literal["signal", "labels"]


def get_capnobase_cache_dir() -> Path:
    """Return the external cache for CapnoBase source tables."""
    cache_dir = (
        Path.home() / ".cache" / "featuregraph" / "capnobase" / CAPNOBASE_VERSION
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def normalize_capnobase_case(case: str | int) -> str:
    """Return a validated four-character CapnoBase case identifier."""
    if isinstance(case, int):
        case = f"{case:04d}"
    if not isinstance(case, str):
        raise TypeError("case must be a string or integer")
    if case not in CAPNOBASE_CASES:
        raise ValueError(
            f"Unknown CapnoBase case {case!r}; choose one of CAPNOBASE_CASES."
        )
    return case


def capnobase_filename(case: str | int, kind: FileKind) -> str:
    """Return the Borealis tabular filename for one case and table."""
    case_id = normalize_capnobase_case(case)
    if kind not in ("signal", "labels"):
        raise ValueError("kind must be 'signal' or 'labels'")
    return f"{case_id}_8min_{kind}.tab"


def _source_file_record(filename: str, *, timeout: int = 120) -> dict:
    response = requests.get(
        f"{CAPNOBASE_API_URL}/datasets/:persistentId/",
        params={"persistentId": CAPNOBASE_DOI, "version": CAPNOBASE_VERSION},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "OK":
        raise RuntimeError("Borealis did not return CapnoBase dataset metadata")

    version = payload["data"]["latestVersion"]
    observed_version = f"{version['versionNumber']}.{version['versionMinorNumber']}"
    if observed_version != CAPNOBASE_VERSION:
        raise RuntimeError(
            "Borealis returned CapnoBase version "
            f"{observed_version}, expected {CAPNOBASE_VERSION}"
        )

    for entry in version["files"]:
        data_file = entry["dataFile"]
        if data_file["filename"] == filename:
            return data_file
    raise RuntimeError(f"CapnoBase source file is absent from Borealis: {filename}")


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_capnobase_file(
    case: str | int,
    kind: FileKind,
    *,
    refresh: bool = False,
    timeout: int = 120,
) -> Path:
    """Download and verify one CapnoBase source table from Borealis."""
    filename = capnobase_filename(case, kind)
    # Borealis stores these as tabulated data but retains the deposited CSV as
    # the original file. The published checksum describes that original.
    destination = get_capnobase_cache_dir() / filename.replace(".tab", ".csv")
    if destination.exists() and destination.stat().st_size > 0 and not refresh:
        return destination

    record = _source_file_record(filename, timeout=timeout)
    url = f"{CAPNOBASE_API_URL}/access/datafile/{record['id']}"
    temporary_path = destination.with_suffix(destination.suffix + ".part")

    try:
        with requests.get(
            url,
            params={"format": "original"},
            stream=True,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            with temporary_path.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output.write(chunk)

        checksum = record.get("checksum", {})
        if checksum.get("type") != "MD5":
            raise RuntimeError(f"Borealis supplied no MD5 checksum for {filename}")
        if _md5(temporary_path) != checksum["value"].lower():
            raise RuntimeError(
                f"Downloaded CapnoBase file failed its Borealis checksum: {url}"
            )
        temporary_path.replace(destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return destination


def load_capnobase_signals(
    case: str | int,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load the capnogram, PPG, and ECG waveforms for one case."""
    case_id = normalize_capnobase_case(case)
    path = download_capnobase_file(case_id, "signal", refresh=refresh)
    source = pd.read_csv(path)
    source.columns = source.columns.str.strip()
    source = source.rename(
        columns={"co2_y": "capnogram", "pleth_y": "ppg", "ecg_y": "ecg"}
    )
    source.insert(0, "case_id", case_id)
    source.insert(1, "sample_index", range(len(source)))
    source.insert(
        2,
        "time_seconds",
        source["sample_index"] / CAPNOBASE_SAMPLING_RATE,
    )
    source.attrs.update(
        {
            "capnobase_case": case_id,
            "capnobase_kind": "signal",
            "capnobase_version": CAPNOBASE_VERSION,
            "sampling_rate_hz": CAPNOBASE_SAMPLING_RATE,
            "source_doi": CAPNOBASE_DOI,
            "source_file": str(path),
        }
    )
    return source


def _sample_numbers(value: object) -> list[int]:
    if pd.isna(value):
        return []
    return [int(number) for number in str(value).strip().split()]


def load_capnobase_labels(
    case: str | int,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load expert event labels as one ordered row per labeled sample."""
    case_id = normalize_capnobase_case(case)
    path = download_capnobase_file(case_id, "labels", refresh=refresh)
    source = pd.read_csv(path)
    source.columns = source.columns.str.strip()

    rows = []
    for column in source.columns:
        if not column.endswith("_x") or column == "units_x":
            continue
        for sample_number in _sample_numbers(source.at[0, column]):
            rows.append(
                {
                    "case_id": case_id,
                    "event_type": column.removesuffix("_x"),
                    "source_sample_number": sample_number,
                    "sample_index": sample_number - 1,
                    "time_seconds": ((sample_number - 1) / CAPNOBASE_SAMPLING_RATE),
                }
            )

    labels = pd.DataFrame.from_records(
        rows,
        columns=[
            "case_id",
            "event_type",
            "source_sample_number",
            "sample_index",
            "time_seconds",
        ],
    ).sort_values(["sample_index", "event_type"], ignore_index=True)
    labels.attrs.update(
        {
            "capnobase_case": case_id,
            "capnobase_kind": "labels",
            "capnobase_version": CAPNOBASE_VERSION,
            "sampling_rate_hz": CAPNOBASE_SAMPLING_RATE,
            "source_doi": CAPNOBASE_DOI,
            "source_file": str(path),
            "source_sample_numbering": "one-based",
        }
    )
    return labels
