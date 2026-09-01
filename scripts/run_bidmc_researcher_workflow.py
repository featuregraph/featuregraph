"""Execute the generated BIDMC study from the frozen researcher input.

This file is implementation infrastructure. Scientific and representational
choices belong in notebooks/bidmc_researcher_input.ipynb.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

from featuregraph.studies import (
    execute_notebook_sources,
    file_sha256,
    git_commit,
    module_versions,
    notebook_sources,
    researcher_values,
    value_sha256,
    write_frames,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_NOTEBOOK = (
    REPO_ROOT / "notebooks" / "researcher_input" / "bidmc_researcher_input.ipynb"
)
EXECUTION_NOTEBOOK = (
    REPO_ROOT / "notebooks" / "generated_study" / "bidmc_generated_study.ipynb"
)
OUTPUT_ROOT = REPO_ROOT / "outputs" / "bidmc_researcher_workflow"


def validate_binding(
    input_source: str, execution_source: str, values: dict[str, object]
) -> None:
    assert len(notebook_sources(INPUT_NOTEBOOK)) == 1
    compile(input_source, str(INPUT_NOTEBOOK), "exec")

    assert values["subject_ids"] == list(range(1, 54))
    assert values["sampling_rate_hz"] == 125
    assert values["smooth_window"] == 100
    assert values["numerical_atol"] == 1e-12
    assert values["expected_samples_per_subject"] == 60001
    assert values["matching"]["tolerance_samples"] == 63
    assert values["comparator"]["filter"] == "fourth-order Butterworth low-pass"
    assert values["comparator"]["cutoff_hz"] == 0.8
    assert values["comparator"]["minimum_distance_samples"] == 188
    assert values["comparator"]["minimum_prominence"] == 0.08
    assert values["state_contract"]["version"] == "state-contract-v1"

    execution_values = researcher_values(execution_source)
    assert values["state_contract"] == execution_values["DEFAULT_BIDMC_STATE_CONTRACT"]

    required_execution_fragments = [
        "FS = 125",
        "W = 100",
        "TOL = 63",
        "NUMERICAL_ATOL = 1e-12",
        "EXPECTED_SIGNAL_ROWS = 60001",
        'butter(4, 0.8, btype="lowpass"',
        "find_peaks(filtered, distance=188, prominence=0.08)",
        "find_peaks(-filtered, distance=188, prominence=0.08)",
        "fg.compile_states(",
        "BIDMC_STATE_CONTRACT",
    ]
    missing = [
        fragment
        for fragment in required_execution_fragments
        if fragment not in execution_source
    ]
    assert not missing, (
        f"Execution notebook is not bound to the researcher input: {missing}"
    )


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    input_sources = notebook_sources(INPUT_NOTEBOOK)
    execution_sources = notebook_sources(EXECUTION_NOTEBOOK)
    input_source = input_sources[0]
    execution_source = "\n\n".join(execution_sources)
    values = researcher_values(input_source)
    validate_binding(input_source, execution_source, values)

    state_contract = values["state_contract"]
    state_contract_path = OUTPUT_ROOT / "state_contract.json"
    state_contract_path.write_text(json.dumps(state_contract, indent=2) + "\n")
    namespace, console_output = execute_notebook_sources(
        execution_sources,
        initial_namespace={"BIDMC_STATE_CONTRACT": state_contract},
        filename=str(EXECUTION_NOTEBOOK),
    )
    (OUTPUT_ROOT / "console_output.txt").write_text(console_output)

    write_frames(
        {
            "subject_summary": namespace["subject_summary"],
            "matched_objects": namespace["matched_objects"],
            "featuregraph_only_objects": namespace["featuregraph_only_objects"],
            "comparator_only_objects": namespace["baseline_only_objects"],
            "invalidated_objects": namespace["invalidated_objects"],
            "annotation_summary": namespace["annotation_summary"],
            "cohort_summary": namespace["cohort_summary"],
            "window_sensitivity": namespace["window_sensitivity"],
        },
        OUTPUT_ROOT,
    )

    all_featuregraph_objects = []
    all_comparator_objects = []
    observation_directory = OUTPUT_ROOT / "observations"
    per_subject_observations = {}
    for subject in values["subject_ids"]:
        observations, objects, _, _ = namespace["construct"](subject)
        comparator_objects, _ = namespace["baseline"](subject)
        objects = objects.copy()
        comparator_objects = comparator_objects.copy()
        comparator_objects["subject_id"] = subject
        all_featuregraph_objects.append(objects)
        all_comparator_objects.append(comparator_objects)
        per_subject_observations[f"subject_{subject:02d}"] = observations

    write_frames(per_subject_observations, observation_directory)

    write_frames(
        {
            "featuregraph_objects": pd.concat(
                all_featuregraph_objects, ignore_index=True
            ),
            "comparator_objects": pd.concat(
                all_comparator_objects, ignore_index=True
            ),
        },
        OUTPUT_ROOT,
    )

    cohort = namespace["cohort_summary"].iloc[0]
    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repository_commit": git_commit(REPO_ROOT),
        "researcher_input_path": str(INPUT_NOTEBOOK.relative_to(REPO_ROOT)),
        "researcher_input_sha256": file_sha256(INPUT_NOTEBOOK),
        "execution_notebook_path": str(EXECUTION_NOTEBOOK.relative_to(REPO_ROOT)),
        "execution_notebook_sha256": file_sha256(EXECUTION_NOTEBOOK),
        "state_contract_path": str(state_contract_path.relative_to(REPO_ROOT)),
        "state_contract_version": state_contract["version"],
        "state_contract_sha256": value_sha256(state_contract),
        "compiled_layer": "directional states and enter/exit boundaries",
        "python": sys.version,
        "platform": platform.platform(),
        **module_versions(pd, np, scipy),
        "subjects": int(cohort["subjects"]),
        "failures": int(cohort["failures"]),
        "featuregraph_complete_objects": int(cohort["featuregraph_complete_objects"]),
        "matched_objects": int(cohort["matched_objects"]),
        "featuregraph_only_objects": int(cohort["featuregraph_only_objects"]),
        "comparator_only_objects": int(cohort["baseline_only_objects"]),
    }
    (OUTPUT_ROOT / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n"
    )

    validation_report = f"""# BIDMC generated-workflow validation

- Researcher input SHA-256: `{provenance["researcher_input_sha256"]}`
- Execution notebook SHA-256: `{provenance["execution_notebook_sha256"]}`
- State contract: `{provenance["state_contract_path"]}`
- State contract version: `{provenance["state_contract_version"]}`
- State contract SHA-256: `{provenance["state_contract_sha256"]}`
- Compiler-backed layer: {provenance["compiled_layer"]}
- Repository commit: `{provenance["repository_commit"]}`
- Subjects: {provenance["subjects"]}
- Execution failures: {provenance["failures"]}
- Complete FeatureGraph objects: {provenance["featuregraph_complete_objects"]}
- Matched objects: {provenance["matched_objects"]}
- FeatureGraph-only objects: {provenance["featuregraph_only_objects"]}
- Comparator-only objects: {provenance["comparator_only_objects"]}

The researcher input contained exactly one code cell. Its declared parameters were
bound to the generated execution notebook before execution. The declared state
contract was compiled for every record, and independent parity assertions checked its
state and event boundaries against the previously frozen formulas. All frozen notebook
regression assertions passed. Every signal download contained 60,001 rows, the RESP
column, and no missing RESP values. Object-level tables and per-subject observation,
state, and event tables are stored beside this report.
"""
    (OUTPUT_ROOT / "validation_report.md").write_text(validation_report)
    print(validation_report)


if __name__ == "__main__":
    main()
