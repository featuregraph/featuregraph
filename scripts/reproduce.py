"""Regenerate FeatureGraph paper tables, figures, and run metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import sys
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import featuregraph as fg


MANIFEST_PATH = Path("reproducibility/manifest.json")
PACKAGES = (
    "featuregraph",
    "numpy",
    "pandas",
    "scipy",
    "requests",
    "pyarrow",
    "openpyxl",
    "matplotlib",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate FeatureGraph paper artifacts."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/paper"),
        help="Output directory (default: artifacts/paper).",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Redownload source datasets instead of using the cache.",
    )
    return parser.parse_args()


def package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package in PACKAGES:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def environment() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or "not-reported",
        "logical_cpu_count": os.cpu_count(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "packages": package_versions(),
    }


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    """Load the versioned authority for reproduction inputs and outputs."""
    if not path.is_file():
        raise FileNotFoundError(f"Reproduction manifest not found: {path}")

    manifest = json.loads(path.read_text(encoding="utf-8"))

    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported reproduction manifest schema.")

    if "seed" not in manifest or "datasets" not in manifest:
        raise ValueError("Manifest must define seed and datasets.")

    if not manifest.get("outputs"):
        raise ValueError("Manifest must define expected outputs.")

    return manifest


def validate_expected_outputs(
    output_dir: Path,
    expected_outputs: list[str],
) -> dict[str, str]:
    """Require every manifest-declared output and return its checksum."""
    missing = [
        relative_path
        for relative_path in expected_outputs
        if not (output_dir / relative_path).is_file()
    ]
    if missing:
        raise RuntimeError(
            "Reproduction did not create expected outputs: "
            + ", ".join(missing)
        )

    return {
        relative_path: sha256(output_dir / relative_path)
        for relative_path in expected_outputs
        if relative_path != "run_metadata.json"
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def validate_object_tables(
    name: str,
    oscillation: Any,
    accumulation: Any,
) -> None:
    """Fail when exported parent and child object tables disagree."""
    oscillations = oscillation.table
    accumulations = accumulation.table

    if oscillations.empty or accumulations.empty:
        raise RuntimeError(f"{name}: generated object tables cannot be empty.")

    if not oscillations["is_complete"].astype(bool).all():
        raise RuntimeError(f"{name}: oscillation table contains partial objects.")

    if not accumulations["is_complete"].astype(bool).all():
        raise RuntimeError(f"{name}: accumulation table contains partial objects.")

    ordered = (
        oscillations["start_index"].lt(oscillations["peak_index"])
        & oscillations["peak_index"].lt(oscillations["end_index"])
    )
    if not ordered.all():
        raise RuntimeError(f"{name}: invalid trough-peak-trough boundary order.")

    expected_durations = {
        "rise_duration": (
            oscillations["peak_index"] - oscillations["start_index"]
        ),
        "fall_duration": (
            oscillations["end_index"] - oscillations["peak_index"]
        ),
        "duration": (
            oscillations["end_index"] - oscillations["start_index"]
        ),
    }
    for column, expected in expected_durations.items():
        if not np.allclose(oscillations[column], expected):
            raise RuntimeError(f"{name}: inconsistent {column} values.")

    group_columns = [
        column
        for column in oscillation.group
        if column in accumulations.columns
    ]
    oscillation_keys = set(
        oscillations[
            [*group_columns, "oscillation_id"]
        ].itertuples(index=False, name=None)
    )
    accumulation_keys = set(
        accumulations[
            [*group_columns, "accumulation_id"]
        ].itertuples(index=False, name=None)
    )
    if oscillation_keys != accumulation_keys:
        raise RuntimeError(
            f"{name}: oscillation and accumulation object IDs differ."
        )


def representative_oscillation(
    observations: Any,
    table: Any,
    plot_signal: str,
) -> Any:
    """Select and validate a deterministic representative oscillation."""
    representative = (
        table.loc[table["is_complete"]]
        .sort_values(
            ["amplitude", "oscillation_id"],
            ascending=[False, True],
        )
        .iloc[0]
    )

    start_index = int(representative["start_index"])
    peak_index = int(representative["peak_index"])
    end_index = int(representative["end_index"])
    segment = observations.loc[start_index:end_index, plot_signal]

    start_value = observations.loc[start_index, plot_signal]
    peak_value = observations.loc[peak_index, plot_signal]
    end_value = observations.loc[end_index, plot_signal]
    maximum_value = segment.max()

    peak_is_maximum = np.isclose(
        peak_value,
        maximum_value,
        rtol=1e-9,
        atol=1e-12,
    )
    endpoints_below_peak = (
        start_value < peak_value
        and end_value < peak_value
    )

    if not peak_is_maximum or not endpoints_below_peak:
        raise RuntimeError(
            "Corrected trough-peak-trough boundaries do not align "
            f"with the displayed values of {plot_signal!r}."
        )

    return representative


def annotated_figure(
    observations: Any,
    table: Any,
    plot_signal: str,
    output_path: Path,
    title: str,
) -> None:

    representative = representative_oscillation(
        observations,
        table,
        plot_signal,
    )

    start = int(representative["start_index"])
    peak = int(representative["peak_index"])
    end = int(representative["end_index"])
    oscillation_id = int(representative["oscillation_id"])

    segment = observations.loc[start:end, plot_signal]

    figure, axis = plt.subplots(
        figsize=(8, 4.5),
        constrained_layout=True,
    )

    axis.plot(
        segment.index,
        segment.to_numpy(),
        color="#3155a4",
        linewidth=1.5,
    )

    axis.scatter(
        [start, peak, end],
        observations.loc[[start, peak, end], plot_signal],
        color=["#2a9d8f", "#e76f51", "#2a9d8f"],
        zorder=3,
    )

    axis.set(
        title=f"{title} — oscillation {oscillation_id}",
        xlabel="Sample index",
        ylabel=plot_signal.replace("_", " ").title(),
    )

    axis.grid(alpha=0.2)
    figure.savefig(output_path, dpi=300)
    plt.close(figure)


def save_objects(
    name: str,
    observations: Any,
    signal: str,
    oscillation: Any,
    accumulation: Any,
    tables_dir: Path,
    figures_dir: Path,
    plot_signal: str | None = None,
) -> dict[str, Any]:
    validate_object_tables(
        name,
        oscillation,
        accumulation,
    )

    oscillation_path = tables_dir / f"{name}_oscillations.csv"
    accumulation_path = tables_dir / f"{name}_accumulations.csv"
    figure_path = figures_dir / f"{name}_annotated_oscillation.png"

    oscillation.table.to_csv(
        oscillation_path,
        index=False,
        lineterminator="\n",
    )
    accumulation.table.to_csv(
        accumulation_path,
        index=False,
        lineterminator="\n",
    )

    annotated_figure(
        observations,
        oscillation.table,
        plot_signal or signal,
        figure_path,
        f"{name.replace('_', ' ').title()} oscillation",
    )

    # Keep the existing return statement unchanged.

    return {
        "oscillation_count": oscillation.count,
        "accumulation_count": accumulation.count,
        "artifacts": {
            str(oscillation_path): sha256(oscillation_path),
            str(accumulation_path): sha256(accumulation_path),
            str(figure_path): sha256(figure_path),
        },
    }


def main() -> None:
    args = parse_args()
    manifest = load_manifest()
    seed = int(manifest["seed"])
    bidmc_selection = manifest["datasets"]["bidmc"]
    eastman_selection = manifest["datasets"]["tennessee_eastman"]

    random.seed(seed)
    np.random.seed(seed)

    output_dir = args.output_dir.resolve()
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    environment_path = output_dir / "environment.json"
    environment_path.write_text(
        json.dumps(environment(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    runs: dict[str, Any] = {}

    started = time.perf_counter()
    bidmc = fg.datasets.bidmc(
        subject=int(bidmc_selection["subject"]),
        refresh=args.refresh,
    )
    bidmc_builder = fg.oscillation.Oscillation(
        signals="respiration",
        group="subject",
        smooth_signal=False,
        diff_lag=1,
    )
    bidmc_features = bidmc_builder.fit_transform(bidmc)
    bidmc_oscillations = bidmc_builder.summarize(
        bidmc_features, signal="respiration"
    )
    bidmc_accumulation_builder = fg.accumulation.Accumulation(
        signals="respiration", group="subject", threshold="min"
    )
    bidmc_accumulation_features = bidmc_accumulation_builder.fit_transform(
        bidmc_features
    )
    bidmc_accumulations = bidmc_accumulation_builder.summarize(
        bidmc_accumulation_features, signal="respiration"
    )
    runs["bidmc"] = save_objects(
        "bidmc",
        bidmc,
        "respiration",
        bidmc_oscillations,
        bidmc_accumulations,
        tables_dir,
        figures_dir,
    )
    runs["bidmc"]["wall_seconds"] = time.perf_counter() - started
    runs["bidmc"]["selection"] = dict(bidmc_selection)
    runs["bidmc"]["source_file"] = bidmc.attrs.get("source_file")

    started = time.perf_counter()
    eastman = fg.datasets.eastman(
        fault_number=int(eastman_selection["fault_number"]),
        simulation_run=int(eastman_selection["simulation_run"]),
        refresh=args.refresh,
    )
    if eastman.attrs.get("source_revision") != eastman_selection["revision"]:
        raise RuntimeError(
            "Tennessee Eastman loader revision does not match "
            "the reproduction manifest."
        )
    eastman_builder = fg.oscillation.Oscillation(
        signals="reactor_temperature",
        group=["fault_number", "simulation_run"],
        smooth_signal=True,
        smooth_window=20,
        diff_lag=1,
    )
    eastman_features = eastman_builder.fit_transform(eastman)
    eastman_oscillations = eastman_builder.summarize(
        eastman_features, signal="reactor_temperature"
    )
    eastman_accumulation_builder = fg.accumulation.Accumulation(
        signals="reactor_temperature",
        group=["fault_number", "simulation_run"],
        threshold="min",
    )
    eastman_accumulation_features = (
        eastman_accumulation_builder.fit_transform(eastman_features)
    )
    eastman_accumulations = eastman_accumulation_builder.summarize(
        eastman_accumulation_features,
        signal="reactor_temperature",
    )
    runs["eastman"] = save_objects(
        "eastman",
        eastman_features,
        "reactor_temperature",
        eastman_oscillations,
        eastman_accumulations,
        tables_dir,
        figures_dir,
        plot_signal="reactor_temperature_smooth",
    )
    runs["eastman"]["wall_seconds"] = time.perf_counter() - started
    runs["eastman"]["selection"] = dict(eastman_selection)
    runs["eastman"]["source_file"] = eastman.attrs.get("source_file")
    runs["eastman"]["source_url"] = eastman.attrs.get("source_url")

    metadata_path = output_dir / "run_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "seed": seed,
                "manifest": str(MANIFEST_PATH),
                "manifest_sha256": sha256(MANIFEST_PATH),
                "python": sys.version,
                "runs": runs,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    checksums = validate_expected_outputs(
        output_dir,
        list(manifest["outputs"]),
    )
    print(
        f"Wrote {len(checksums) + 1} reproducibility artifacts "
        f"to {output_dir}"
    )


if __name__ == "__main__":
    main()
