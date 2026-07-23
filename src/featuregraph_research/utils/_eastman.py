from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests


GITHUB_OWNER = "mv-per"
GITHUB_REPOSITORY = "tennessee-eastman-dataset"
GITHUB_BRANCH = "main"

# media.githubusercontent.com resolves Git LFS files to their actual contents.
GITHUB_MEDIA_BASE_URL = (
    "https://media.githubusercontent.com/media/"
    f"{GITHUB_OWNER}/{GITHUB_REPOSITORY}/{GITHUB_BRANCH}"
)

# XLSX files are ZIP archives and normally begin with this signature.
XLSX_SIGNATURE = b"PK"


def get_tep_cache_dir() -> Path:
    """
    Return the external cache used for Tennessee Eastman run files.

    The cache is stored outside the Git repository.
    """
    cache_dir = (
        Path.home()
        / ".cache"
        / "featuregraph"
        / "tennessee_eastman"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def tep_run_filename(
    *,
    fault_number: int,
    simulation_run: int,
    mode: int = 1,
) -> str:
    """
    Return the source filename for one Tennessee Eastman fault run.
    """
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
) -> str:
    """
    Return the direct Git LFS media URL for one fault run.
    """
    filename = tep_run_filename(
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
    )

    return (
        f"{GITHUB_MEDIA_BASE_URL}/"
        f"simulations/mode_{mode}/faults/{filename}"
    )


def list_tep_files(
    *,
    mode: int = 1,
    fault_numbers: range = range(1, 22),
    simulation_runs: range = range(1, 11),
) -> pd.DataFrame:
    """
    Return the expected run-file names and direct download URLs.

    This function does not download any files.
    """
    rows: list[dict[str, object]] = []

    for fault_number in fault_numbers:
        for simulation_run in simulation_runs:
            rows.append(
                {
                    "mode": mode,
                    "fault_number": fault_number,
                    "simulation_run": simulation_run,
                    "filename": tep_run_filename(
                        fault_number=fault_number,
                        simulation_run=simulation_run,
                        mode=mode,
                    ),
                    "url": tep_run_url(
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
    refresh: bool = False,
    timeout: int = 300,
) -> Path:
    """
    Download exactly one Tennessee Eastman simulation run.

    The function downloads the real Git LFS object directly instead of
    cloning the complete repository. Existing cached files are reused
    unless ``refresh=True``.

    Returns
    -------
    pathlib.Path
        Path to the cached XLSX workbook.
    """
    filename = tep_run_filename(
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
    )

    destination = get_tep_cache_dir() / filename

    if destination.exists() and not refresh:
        _validate_xlsx_file(destination)
        return destination

    url = tep_run_url(
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

            content_type = response.headers.get(
                "content-type",
                "",
            ).lower()

            with temporary_path.open("wb") as file:
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
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
    """
    Download, cache, and load one Tennessee Eastman fault run.

    Parameters
    ----------
    dataset:
        Retained for compatibility with the earlier FeatureGraph API.
        Currently only ``"faulty_training"`` is supported by this
        single-run source.

    fault_number:
        Fault identifier.

    simulation_run:
        Simulation-run identifier.

    mode:
        Tennessee Eastman operating mode. The default is mode 1.

    refresh:
        Redownload the workbook even when it is already cached.

    standardize_columns:
        Convert source column names to consistent snake_case names.

    Returns
    -------
    pandas.DataFrame
        Observations for exactly one fault and simulation run.
    """
    if dataset != "faulty_training":
        raise ValueError(
            "The single-run loader currently supports only "
            "'faulty_training'. "
            f"Received {dataset!r}."
        )

    path = download_tep_run(
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
        refresh=refresh,
    )

    try:
        df = pd.read_excel(
            path,
            engine="openpyxl",
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to read Tennessee Eastman workbook: {path}"
        ) from exc

    if standardize_columns:
        df = standardize_tep_columns(df)

    # Each workbook already represents exactly one run.
    if "fault_number" not in df.columns:
        df.insert(0, "fault_number", fault_number)
    else:
        df["fault_number"] = fault_number

    if "simulation_run" not in df.columns:
        insertion_position = (
            1 if "fault_number" in df.columns else 0
        )
        df.insert(
            insertion_position,
            "simulation_run",
            simulation_run,
        )
    else:
        df["simulation_run"] = simulation_run

    df = df.reset_index(drop=True)

    df.attrs["tep_dataset"] = dataset
    df.attrs["tep_mode"] = mode
    df.attrs["fault_number"] = fault_number
    df.attrs["simulation_run"] = simulation_run
    df.attrs["source_file"] = str(path)
    df.attrs["source_url"] = tep_run_url(
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
    )

    return df


def standardize_tep_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Standardize Tennessee Eastman column names.

    Examples
    --------
    ``faultNumber`` becomes ``fault_number``.
    ``simulationRun`` becomes ``simulation_run``.
    ``XMEAS.1`` becomes ``xmeas_1``.
    """
    explicit_rename = {
        "faultNumber": "fault_number",
        "simulationRun": "simulation_run",
    }

    result = df.rename(columns=explicit_rename).copy()

    result.columns = [
        _snake_case_column(column)
        for column in result.columns
    ]

    return result


def save_tep_run_as_parquet(
    *,
    fault_number: int,
    simulation_run: int,
    mode: int = 1,
    output_path: str | Path | None = None,
    refresh: bool = False,
) -> Path:
    """
    Load one run and save it as a compact Parquet file.

    When ``output_path`` is omitted, the Parquet file is written beneath
    the FeatureGraph cache directory.
    """
    df = load_tep_run(
        fault_number=fault_number,
        simulation_run=simulation_run,
        mode=mode,
        refresh=refresh,
    )

    if output_path is None:
        output_path = (
            get_tep_cache_dir()
            / (
                f"mode{mode}_fault_{fault_number}"
                f"_run_{simulation_run}.parquet"
            )
        )
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_parquet(
        output_path,
        index=False,
    )

    return output_path


def clear_tep_cache() -> None:
    """
    Remove all cached Tennessee Eastman files.
    """
    cache_dir = get_tep_cache_dir()

    for path in cache_dir.iterdir():
        if path.is_file():
            path.unlink()


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

    if not isinstance(mode, int):
        raise TypeError("mode must be an integer")

    if fault_number < 1:
        raise ValueError("fault_number must be at least 1")

    if simulation_run < 1:
        raise ValueError("simulation_run must be at least 1")

    if mode < 1:
        raise ValueError("mode must be at least 1")


def _validate_xlsx_file(
    path: Path,
    *,
    source_url: str | None = None,
    content_type: str | None = None,
) -> None:
    """
    Confirm that a downloaded file is a real XLSX workbook.

    This explicitly detects Git LFS pointer files so that a 132-byte
    pointer can never be passed to pandas as an Excel workbook.
    """
    if not path.exists():
        raise FileNotFoundError(path)

    size = path.stat().st_size

    if size == 0:
        raise ValueError(
            f"Downloaded file is empty: {path}"
        )

    prefix = path.read_bytes()[:256]

    if prefix.startswith(
        b"version https://git-lfs.github.com/spec/v1"
    ):
        raise RuntimeError(
            "GitHub returned a Git LFS pointer instead of the actual "
            f"workbook: {path}. Source URL: {source_url}"
        )

    if not prefix.startswith(XLSX_SIGNATURE):
        details = (
            f"size={size}, "
            f"content_type={content_type!r}, "
            f"source_url={source_url!r}"
        )

        raise ValueError(
            "Downloaded file is not a valid XLSX workbook. "
            f"{details}"
        )


def _snake_case_column(column: object) -> str:
    value = str(column).strip().lower()

    for character in (" ", ".", "-", "/", "\\"):
        value = value.replace(character, "_")

    while "__" in value:
        value = value.replace("__", "_")

    return value.strip("_")