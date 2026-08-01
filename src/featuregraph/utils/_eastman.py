from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

GITHUB_OWNER = "mv-per"
GITHUB_REPOSITORY = "tennessee-eastman-dataset"
GITHUB_REVISION = "309b944f35ac440ff0c70616947ffe723c766e14"

GITHUB_MEDIA_BASE_URL = (
    "https://media.githubusercontent.com/media/"
    f"{GITHUB_OWNER}/{GITHUB_REPOSITORY}/{GITHUB_REVISION}"
)

XLSX_SIGNATURE = b"PK"
SUPPORTED_DATASETS = {"faulty_training", "faultfree_training"}
_DATASET_ALIASES = {
    "faulty_training": "faulty_training",
    "fault_free_training": "faultfree_training",
    "faultfree_training": "faultfree_training",
}


def get_tep_cache_dir() -> Path:
    """Return the external cache used for Tennessee Eastman files."""
    cache_dir = (
        Path.home()
        / ".cache"
        / "featuregraph"
        / "tennessee_eastman"
        / GITHUB_REVISION
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def normalize_tep_dataset(dataset: str) -> str:
    """Return the canonical Tennessee Eastman dataset name."""
    if not isinstance(dataset, str):
        raise TypeError("dataset must be a string")

    normalized = dataset.strip().lower().replace("-", "_")

    try:
        return _DATASET_ALIASES[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(SUPPORTED_DATASETS))
        raise ValueError(
            f"Unsupported Tennessee Eastman dataset {dataset!r}. "
            f"Supported datasets are: {supported}."
        ) from exc


def tep_run_filename(
    *,
    fault_number: int,
    simulation_run: int,
    mode: int = 1,
    dataset: str = "faulty_training",
) -> str:
    """Return the source filename for one Tennessee Eastman run."""
    dataset = normalize_tep_dataset(dataset)

    if dataset == "faultfree_training":
        _validate_mode(mode)
        return f"mode{mode}_normal_50.xlsx"

    _validate_run_identifiers(
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
    )
    return f"mode{mode}_{fault_number}_{simulation_run}.xlsx"


def tep_run_url(
    *,
    fault_number: int,
    simulation_run: int,
    mode: int = 1,
    dataset: str = "faulty_training",
) -> str:
    """Return the direct Git LFS media URL for one run."""
    dataset = normalize_tep_dataset(dataset)
    filename = tep_run_filename(
        dataset=dataset,
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
    )

    if dataset == "faultfree_training":
        relative_path = f"simulations/mode_{mode}/{filename}"
    else:
        relative_path = f"simulations/mode_{mode}/faults/{filename}"

    return f"{GITHUB_MEDIA_BASE_URL}/{relative_path}"


def list_tep_files(
    *,
    mode: int = 1,
    fault_numbers: range = range(1, 22),
    simulation_runs: range = range(1, 11),
    dataset: str = "faulty_training",
) -> pd.DataFrame:
    """Return expected Tennessee Eastman filenames and URLs."""
    dataset = normalize_tep_dataset(dataset)

    if dataset == "faultfree_training":
        return pd.DataFrame(
            [
                {
                    "dataset": dataset,
                    "mode": mode,
                    "fault_number": 0,
                    "simulation_run": 1,
                    "filename": tep_run_filename(
                        dataset=dataset,
                        fault_number=0,
                        simulation_run=1,
                        mode=mode,
                    ),
                    "url": tep_run_url(
                        dataset=dataset,
                        fault_number=0,
                        simulation_run=1,
                        mode=mode,
                    ),
                }
            ]
        )

    rows: list[dict[str, object]] = []
    for fault_number in fault_numbers:
        for simulation_run in simulation_runs:
            rows.append(
                {
                    "dataset": dataset,
                    "mode": mode,
                    "fault_number": fault_number,
                    "simulation_run": simulation_run,
                    "filename": tep_run_filename(
                        dataset=dataset,
                        fault_number=fault_number,
                        simulation_run=simulation_run,
                        mode=mode,
                    ),
                    "url": tep_run_url(
                        dataset=dataset,
                        fault_number=fault_number,
                        simulation_run=simulation_run,
                        mode=mode,
                    ),
                }
            )
    return pd.DataFrame(rows)


def download_tep_run(
    *,
    fault_number: int,
    simulation_run: int,
    mode: int = 1,
    dataset: str = "faulty_training",
    refresh: bool = False,
    timeout: int = 300,
) -> Path:
    """Download exactly one Tennessee Eastman workbook."""
    dataset = normalize_tep_dataset(dataset)
    filename = tep_run_filename(
        dataset=dataset,
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
    )
    destination = get_tep_cache_dir() / dataset / filename
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not refresh:
        _validate_xlsx_file(destination)
        return destination

    url = tep_run_url(
        dataset=dataset,
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
    )
    temporary_path = destination.with_suffix(".xlsx.part")

    try:
        with requests.get(
            url,
            stream=True,
            timeout=timeout,
            allow_redirects=True,
        ) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            with temporary_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        file.write(chunk)

        _validate_xlsx_file(
            temporary_path,
            source_url=url,
            content_type=content_type,
        )
        temporary_path.replace(destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return destination


def load_tep_run(
    dataset: str = "faulty_training",
    *,
    fault_number: int,
    simulation_run: int,
    mode: int = 1,
    refresh: bool = False,
    standardize_columns: bool = True,
) -> pd.DataFrame:
    """Download, cache, and load one Tennessee Eastman run.

    ``faultfree_training`` loads the repository's normal-operation
    training workbook. Its returned ``fault_number`` is always zero;
    the supplied fault number is accepted for API compatibility.
    """
    dataset = normalize_tep_dataset(dataset)
    path = download_tep_run(
        dataset=dataset,
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
        refresh=refresh,
    )

    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as exc:
        raise RuntimeError(
            f"Failed to read Tennessee Eastman workbook: {path}"
        ) from exc

    if dataset == "faultfree_training":
        df = _relabel_faultfree_measurement_columns(df)

    if standardize_columns:
        df = standardize_tep_columns(df)

    effective_fault_number = 0 if dataset == "faultfree_training" else fault_number

    if "fault_number" not in df.columns:
        df.insert(0, "fault_number", effective_fault_number)
    else:
        df["fault_number"] = effective_fault_number

    if "simulation_run" not in df.columns:
        df.insert(1, "simulation_run", simulation_run)
    else:
        df["simulation_run"] = simulation_run

    df = df.reset_index(drop=True)
    df.attrs["tep_dataset"] = dataset
    df.attrs["tep_mode"] = mode
    df.attrs["fault_number"] = effective_fault_number
    df.attrs["simulation_run"] = simulation_run
    df.attrs["source_file"] = str(path)
    df.attrs["source_revision"] = GITHUB_REVISION
    df.attrs["source_url"] = tep_run_url(
        dataset=dataset,
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
    )
    return df


def _relabel_faultfree_measurement_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Correct mislabeled measurement headers in the normal workbook.

    The source normal-operation workbook stores the 41 XMEAS channels
    under XMV-style headers. Their order still follows XMEAS(1)..XMEAS(41),
    so relabel them before applying the shared Tennessee Eastman rename map.
    """
    expected_columns = ["time", *[f"xmv_{index}" for index in range(1, 42)]]
    actual_columns = [_snake_case_column(column) for column in df.columns]

    if actual_columns != expected_columns:
        raise ValueError(
            "Unexpected fault-free Tennessee Eastman workbook schema. "
            "Expected time followed by xmv_1 through xmv_41."
        )

    result = df.copy()
    result.columns = ["time", *[f"xmeas_{index}" for index in range(1, 42)]]
    return result


def standardize_tep_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize Tennessee Eastman column names."""
    result = df.rename(
        columns={
            "faultNumber": "fault_number",
            "simulationRun": "simulation_run",
        }
    ).copy()
    result.columns = [_snake_case_column(column) for column in result.columns]
    return result


def save_tep_run_as_parquet(
    *,
    fault_number: int,
    simulation_run: int,
    mode: int = 1,
    dataset: str = "faulty_training",
    output_path: str | Path | None = None,
    refresh: bool = False,
) -> Path:
    """Load one run and save it as a Parquet file."""
    dataset = normalize_tep_dataset(dataset)
    df = load_tep_run(
        dataset=dataset,
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
        refresh=refresh,
    )

    if output_path is None:
        output_path = (
            get_tep_cache_dir()
            / dataset
            / f"mode{mode}_fault_{df.attrs['fault_number']}_run_{simulation_run}.parquet"
        )
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    return output_path


def clear_tep_cache() -> None:
    """Remove all cached Tennessee Eastman files."""
    cache_dir = get_tep_cache_dir()
    for path in sorted(cache_dir.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()


def _validate_mode(mode: int) -> None:
    if not isinstance(mode, int):
        raise TypeError("mode must be an integer")
    if mode < 1:
        raise ValueError("mode must be at least 1")


def _validate_run_identifiers(
    *,
    fault_number: int,
    simulation_run: int,
    mode: int,
) -> None:
    if not isinstance(fault_number, int):
        raise TypeError("fault_number must be an integer")
    if not isinstance(simulation_run, int):
        raise TypeError("simulation_run must be an integer")
    _validate_mode(mode)
    if fault_number < 1:
        raise ValueError("fault_number must be at least 1")
    if simulation_run < 1:
        raise ValueError("simulation_run must be at least 1")


def _validate_xlsx_file(
    path: Path,
    *,
    source_url: str | None = None,
    content_type: str | None = None,
) -> None:
    """Confirm that a downloaded file is a real XLSX workbook."""
    if not path.exists():
        raise FileNotFoundError(path)
    size = path.stat().st_size
    if size == 0:
        raise ValueError(f"Downloaded file is empty: {path}")

    prefix = path.read_bytes()[:256]
    if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise RuntimeError(
            "GitHub returned a Git LFS pointer instead of the actual "
            f"workbook: {path}. Source URL: {source_url}"
        )
    if not prefix.startswith(XLSX_SIGNATURE):
        raise ValueError(
            "Downloaded file is not a valid XLSX workbook. "
            f"size={size}, content_type={content_type!r}, "
            f"source_url={source_url!r}"
        )


def _snake_case_column(column: object) -> str:
    value = str(column).strip().lower()
    for character in (" ", ".", "-", "/", "\\"):
        value = value.replace(character, "_")
    while "__" in value:
        value = value.replace("__", "_")
    return value.strip("_")
