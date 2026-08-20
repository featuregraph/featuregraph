"""Execute and verify the frozen TEP transfer study from researcher input."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from featuregraph.contracts.study_workflow import (
    declarative_values,
    execute_notebook_sources,
    file_sha256,
    notebook_sources,
    write_json_artifact,
)
from featuregraph.utils._eastman import standardize_tep_columns
from featuregraph.utils._rename_map import eastman_map

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_NOTEBOOK = (
    REPO_ROOT / "notebooks" / "researcher_input" / "tep_researcher_input.ipynb"
)
EXECUTION_NOTEBOOK = (
    REPO_ROOT / "notebooks" / "generated_study" / "tep_generated_study.ipynb"
)
OUTPUT_ROOT = REPO_ROOT / "outputs" / "tep_researcher_workflow"
NORMAL_URL = (
    "https://media.githubusercontent.com/media/mv-per/"
    "tennessee-eastman-dataset/main/simulations/mode_1/mode1_normal_500.xlsx"
)


def validate_binding(
    input_source: str, execution_source: str, values: dict[str, object]
) -> None:
    assert len(notebook_sources(INPUT_NOTEBOOK)) == 1
    compile(input_source, str(INPUT_NOTEBOOK), "exec")
    contract = values["state_contract"]
    assert contract["version"] == "state-contract-v1"
    assert contract["parameters"]["rate_eps"] == 0.0
    execution_values = declarative_values(execution_source, EXECUTION_NOTEBOOK)
    assert contract == execution_values["DEFAULT_TEP_STATE_CONTRACT"]
    required = [
        "fg.compile_states(",
        "TEP_STATE_CONTRACT",
        ".rolling(ROLLING_MAX_WINDOW",
        ".rolling(ROLLING_MEAN_WINDOW",
        ".shift(-OFFLINE_ALIGNMENT_SHIFT)",
    ]
    missing = [fragment for fragment in required if fragment not in execution_source]
    assert not missing, f"Generated TEP study is missing bound logic: {missing}"


def load_normal_record(destination: Path) -> pd.DataFrame:
    """Load the upstream 500-hour normal record with its positional column repair."""
    if not destination.exists():
        with requests.get(NORMAL_URL, stream=True, timeout=300) as response:
            response.raise_for_status()
            with destination.open("wb") as file:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        file.write(chunk)
    frame = pd.read_excel(destination, engine="openpyxl")
    if len(frame.columns) != 42:
        raise ValueError("Expected Time plus 41 process-measurement columns.")
    # The upstream normal workbook labels all process measurements xmv-1..41;
    # their position and values follow the xmeas-1..41 schema used by fault runs.
    frame.columns = ["time_(h)", *[f"xmeas_{i}" for i in range(1, 42)]]
    return standardize_tep_columns(frame).rename(columns=eastman_map)


def run_metrics(
    source: pd.DataFrame,
    construct_observations,
    summarize_candidates,
    validate_study,
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    original_pressure = source["reactor_pressure"].copy(deep=True)
    observations, _, provenance = construct_observations(source)
    candidates = summarize_candidates(observations)
    validation = validate_study(
        source, observations, original_pressure, candidates
    )
    peaks = candidates.dropna(subset=["peak_smooth_pressure"]).copy()
    preceding_minimum = candidates.set_index("candidate_id")["smooth_minimum"]
    peaks["preceding_trough_prominence"] = peaks.apply(
        lambda row: row["peak_smooth_pressure"]
        - preceding_minimum.get(row["candidate_id"] - 1, np.nan),
        axis=1,
    )
    dominant = peaks.nlargest(1, "peak_smooth_pressure").iloc[0]
    metrics = {
        **provenance,
        "source_observations": len(observations),
        "valid_observations": int(observations["reactor_pressure_valid"].sum()),
        "peak_events": int(observations["reactor_pressure_peak"].sum()),
        "complete_cycles": int(candidates["is_complete"].sum()),
        "boundary_fragments": int(candidates["boundary_fragment"].sum()),
        "maximum_aligned_peak": float(dominant["peak_smooth_pressure"]),
        "peak_index": int(dominant["peak_index"]),
        "peak_excess_over_run_median": float(
            dominant["peak_smooth_pressure"]
            - observations["reactor_pressure_smooth"].median()
        ),
        "maximum_preceding_trough_prominence": float(
            peaks["preceding_trough_prominence"].max()
        ),
    }
    return metrics, observations, candidates, validation


def assert_frozen_results(
    fault2: pd.DataFrame, normal: pd.DataFrame, contrasting: pd.DataFrame
) -> None:
    expected_fault2 = pd.DataFrame(
        [
            (1, 28, 2806.300, 641, 4.639, 4.822),
            (2, 24, 2807.414, 644, 5.621, 6.318),
            (3, 26, 2806.804, 630, 5.001, 4.623),
            (4, 24, 2805.597, 687, 3.914, 2.645),
            (5, 29, 2807.597, 650, 5.876, 6.704),
            (6, 30, 2806.187, 631, 4.599, 5.365),
            (7, 27, 2804.962, 645, 3.258, 3.071),
            (8, 27, 2807.028, 645, 5.336, 5.773),
            (9, 24, 2805.790, 650, 4.106, 4.225),
            (10, 32, 2806.578, 637, 4.825, 4.029),
        ],
        columns=[
            "simulation_run",
            "peak_events",
            "maximum_aligned_peak",
            "peak_index",
            "peak_excess_over_run_median",
            "maximum_preceding_trough_prominence",
        ],
    )
    actual_fault2 = fault2[expected_fault2.columns].copy()
    float_columns = expected_fault2.select_dtypes(include="float").columns
    actual_fault2[float_columns] = actual_fault2[float_columns].round(3)
    pd.testing.assert_frame_equal(
        actual_fault2.reset_index(drop=True), expected_fault2, check_dtype=False
    )

    expected_normal = {
        "maximum_aligned_peak": (2803.047, 2803.132, 2803.689),
        "peak_excess_over_run_median": (1.294, 1.482, 1.950),
        "maximum_preceding_trough_prominence": (1.875, 2.256, 3.060),
        "peak_events": (25.0, 28.0, 31.0),
    }
    for column, expected in expected_normal.items():
        observed = (
            float(normal[column].min()),
            float(normal[column].median()),
            float(normal[column].max()),
        )
        assert tuple(round(value, 3) for value in observed) == expected

    threshold = float(
        fault2.loc[
            fault2["simulation_run"].eq(10), "peak_excess_over_run_median"
        ].iloc[0]
    )
    observed_faults = contrasting.loc[
        contrasting["peak_excess_over_run_median"].ge(threshold), "fault_number"
    ].tolist()
    assert observed_faults == [1, 2, 7, 8, 11, 12, 13, 17, 18, 20]


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    input_source = notebook_sources(INPUT_NOTEBOOK)[0]
    execution_sources = notebook_sources(EXECUTION_NOTEBOOK)
    execution_source = "\n\n".join(execution_sources)
    values = declarative_values(input_source, INPUT_NOTEBOOK)
    validate_binding(input_source, execution_source, values)
    contract = values["state_contract"]
    contract_path = OUTPUT_ROOT / "state_contract.json"
    contract_sha256 = write_json_artifact(contract_path, contract)

    namespace, _ = execute_notebook_sources(
        execution_sources[:1],
        EXECUTION_NOTEBOOK,
        initial_namespace={"TEP_STATE_CONTRACT": contract},
    )
    load_run = namespace["load_run"]
    construct = namespace["construct_observations"]
    summarize = namespace["summarize_candidates"]
    validate = namespace["validate_study"]

    fault2_rows = []
    source_manifest = []
    for simulation_run in range(1, 11):
        source = load_run(fault_number=2, simulation_run=simulation_run)
        metrics, _, _, _ = run_metrics(source, construct, summarize, validate)
        fault2_rows.append(metrics)
        source_path = Path(source.attrs["source_file"])
        source_manifest.append(
            {
                "cohort": "fault_2",
                "fault_number": 2,
                "simulation_run": simulation_run,
                "source_url": source.attrs["source_url"],
                "source_sha256": file_sha256(source_path),
            }
        )
    fault2 = pd.DataFrame(fault2_rows).sort_values("simulation_run")

    normal_path = OUTPUT_ROOT / "mode1_normal_500.xlsx"
    normal_source = load_normal_record(normal_path)
    normal_rows = []
    for window in range(10):
        start_hour = window * 50
        end_hour = (window + 1) * 50
        frame = normal_source.loc[
            normal_source["time_(h)"].ge(start_hour)
            & normal_source["time_(h)"].lt(end_hour)
        ].copy()
        frame = frame.reset_index(drop=True)
        frame["time_(h)"] -= start_hour
        frame["fault_number"] = 0
        frame["simulation_run"] = window + 1
        metrics, _, _, _ = run_metrics(frame, construct, summarize, validate)
        metrics["window"] = window + 1
        normal_rows.append(metrics)
    normal = pd.DataFrame(normal_rows).sort_values("window")
    source_manifest.append(
        {
            "cohort": "normal_500_hour_record",
            "fault_number": 0,
            "simulation_run": 0,
            "source_url": NORMAL_URL,
            "source_sha256": file_sha256(normal_path),
        }
    )

    contrasting_rows = []
    for fault_number in range(1, 22):
        source = load_run(fault_number=fault_number, simulation_run=10)
        metrics, _, _, _ = run_metrics(source, construct, summarize, validate)
        contrasting_rows.append(metrics)
        if fault_number != 2:
            source_path = Path(source.attrs["source_file"])
            source_manifest.append(
                {
                    "cohort": "contrasting_faults",
                    "fault_number": fault_number,
                    "simulation_run": 10,
                    "source_url": source.attrs["source_url"],
                    "source_sha256": file_sha256(source_path),
                }
            )
    contrasting = pd.DataFrame(contrasting_rows).sort_values("fault_number")
    assert_frozen_results(fault2, normal, contrasting)

    fault2.to_csv(OUTPUT_ROOT / "fault2_runs.csv", index=False)
    normal.to_csv(OUTPUT_ROOT / "normal_windows.csv", index=False)
    contrasting.to_csv(OUTPUT_ROOT / "contrasting_faults.csv", index=False)
    pd.DataFrame(source_manifest).to_csv(
        OUTPUT_ROOT / "source_manifest.csv", index=False
    )

    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "researcher_input_path": str(INPUT_NOTEBOOK.relative_to(REPO_ROOT)),
        "researcher_input_sha256": file_sha256(INPUT_NOTEBOOK),
        "execution_notebook_path": str(EXECUTION_NOTEBOOK.relative_to(REPO_ROOT)),
        "execution_notebook_sha256": file_sha256(EXECUTION_NOTEBOOK),
        "state_contract_path": str(contract_path.relative_to(REPO_ROOT)),
        "state_contract_sha256": contract_sha256,
        "state_contract_version": contract["version"],
        "compiled_layer": "directional states and native enter/exit boundaries",
        "peak_projection": "native exit boundary shifted to following valid sample",
        "source_files": len(source_manifest),
        "python": sys.version,
        "platform": platform.platform(),
        "pandas": pd.__version__,
    }
    (OUTPUT_ROOT / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n"
    )
    development = fault2.loc[fault2["simulation_run"].eq(10)].iloc[0]
    report = f"""# TEP compiler-backed transfer validation

- State contract SHA-256: `{contract_sha256}`
- Fault 2 runs: {len(fault2)}
- Normal windows: {len(normal)}
- Contrasting fault classes: {len(contrasting)}
- Development peak events: {int(development['peak_events'])}
- Development complete cycles: {int(development['complete_cycles'])}

The compiler reproduced the frozen state and event formulas at every sample in
every run and normal window. All published transfer-table regressions passed.
The result remains an abnormal-pressure representation, not a Fault 2 classifier.
"""
    (OUTPUT_ROOT / "validation_report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
