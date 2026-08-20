"""Execute and verify the frozen CLaP state-occurrence study."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_mutual_info_score, adjusted_rand_score

import featuregraph as fg
from featuregraph.behaviors.feature_object import ObjectStatus
from featuregraph.contracts.study_workflow import (
    declarative_values,
    execute_notebook_sources,
    file_sha256,
    notebook_sources,
    value_sha256,
    write_json_artifact,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_NOTEBOOK = (
    REPO_ROOT / "notebooks" / "researcher_input" / "clap_researcher_input.ipynb"
)
EXECUTION_NOTEBOOK = (
    REPO_ROOT / "notebooks" / "generated_study" / "clap_generated_study.ipynb"
)
OUTPUT_ROOT = REPO_ROOT / "outputs" / "clap_researcher_workflow"


def validate_binding(
    input_source: str, execution_source: str, values: dict[str, object]
) -> None:
    compile(input_source, str(INPUT_NOTEBOOK), "exec")
    contract = values["state_contract"]
    assert contract["version"] == "state-contract-v1"
    assert contract["state_column"] == "state_label"
    execution_values = declarative_values(execution_source, EXECUTION_NOTEBOOK)
    assert contract == execution_values["DEFAULT_CLAP_STATE_CONTRACT"]
    required = [
        "AgglomerativeCLaPDetection()",
        "fg.from_state_sequence(",
        "state_contract=CLAP_STATE_CONTRACT",
        'specification_id="clap-crop-state-occurrence-v1"',
    ]
    missing = [fragment for fragment in required if fragment not in execution_source]
    assert not missing, f"Generated CLaP study is missing bound logic: {missing}"


def assert_frozen_results(
    source: dict[str, object],
    clap_states: np.ndarray,
    sparse_states: set[object],
    sparse_transitions: set[object],
    result,
    comparison: pd.DataFrame,
) -> dict[str, float | int]:
    observations = result.observations
    objects = result.object_table()
    expected_reference = np.array(
        [1725, 3450, 5175, 8625, 12075, 15525, 17250, 18975]
    )
    expected_clap = np.array(
        [1704, 3446, 5173, 8600, 12001, 15523, 17240, 18996]
    )
    predicted = observations.loc[
        observations["enter_state_occurrence"]
        & observations["sample_index"].gt(0),
        "sample_index",
    ].to_numpy()
    ari = adjusted_rand_score(source["reference_states"], clap_states)
    ami = adjusted_mutual_info_score(source["reference_states"], clap_states)

    assert version("claspy") == "0.2.8"
    assert len(observations) == 20_700
    assert source["window_size"] == 10
    assert np.array_equal(source["true_change_points"], expected_reference)
    assert np.array_equal(predicted, expected_clap)
    assert set(map(int, sparse_states)) == {1, 2, 3}
    assert set(map(tuple, sparse_transitions)) == {(1, 2), (2, 3), (3, 1)}
    assert len(objects) == 9
    assert objects["status"].eq(ObjectStatus.COMPLETE.value).sum() == 7
    assert objects["status"].eq(ObjectStatus.BOUNDARY_TRUNCATED.value).sum() == 2
    assert len(result.relations) == 8
    assert np.array_equal(result.reconstruct_states(), clap_states)
    assert round(float(ari), 6) == 0.977131
    assert round(float(ami), 6) == 0.959136
    assert float(comparison["absolute_error_samples"].median()) == 15.5
    assert int(comparison["absolute_error_samples"].max()) == 74
    return {
        "observations": len(observations),
        "state_occurrence_objects": len(objects),
        "complete_internal_occurrences": 7,
        "boundary_fragments": 2,
        "adjacent_relations": len(result.relations),
        "adjusted_rand_index": float(ari),
        "adjusted_mutual_information": float(ami),
        "median_absolute_boundary_error_samples": 15.5,
        "maximum_absolute_boundary_error_samples": 74,
    }


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    input_sources = notebook_sources(INPUT_NOTEBOOK)
    execution_sources = notebook_sources(EXECUTION_NOTEBOOK)
    input_source = "\n\n".join(input_sources)
    execution_source = "\n\n".join(execution_sources)
    values = declarative_values(input_source, INPUT_NOTEBOOK)
    validate_binding(input_source, execution_source, values)
    contract = values["state_contract"]
    contract_path = OUTPUT_ROOT / "state_contract.json"
    contract_sha256 = write_json_artifact(contract_path, contract)

    namespace, _ = execute_notebook_sources(
        execution_sources[:1],
        EXECUTION_NOTEBOOK,
        initial_namespace={"CLAP_STATE_CONTRACT": contract},
    )
    source = namespace["load_crop"]()
    detector, clap_states, sparse_states, sparse_transitions = namespace["run_clap"](
        source["signal"]
    )
    result = fg.from_state_sequence(
        clap_states,
        signal=source["signal"],
        group_id="CLAP-CROP",
        dataset=source["dataset"],
        signal_name="Crop signal",
        detector=f"claspy.{type(detector).__name__}",
        specification_id="clap-crop-state-occurrence-v1",
        software_version=f"claspy-{version('claspy')}",
        object_type="clap_state_occurrence",
        state_contract=contract,
    )
    observations = result.observations.copy()
    observations["reference_state"] = source["reference_states"]
    predicted = observations.loc[
        observations["enter_state_occurrence"]
        & observations["sample_index"].gt(0),
        "sample_index",
    ].to_numpy()
    comparison = namespace["compare_boundaries"](
        predicted, source["true_change_points"]
    )
    validation = namespace["validate_study"](
        source, clap_states, result, sparse_transitions
    )
    summary = assert_frozen_results(
        source,
        clap_states,
        sparse_states,
        sparse_transitions,
        result,
        comparison,
    )

    observations.to_csv(
        OUTPUT_ROOT / "observations.csv.gz", index=False, compression="gzip"
    )
    result.object_table().to_csv(OUTPUT_ROOT / "objects.csv", index=False)
    result.relations.to_csv(OUTPUT_ROOT / "relations.csv", index=False)
    comparison.to_csv(OUTPUT_ROOT / "boundary_comparison.csv", index=False)
    validation.to_csv(OUTPUT_ROOT / "validation.csv")
    (OUTPUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    label_sha256 = value_sha256(clap_states.tolist())
    source_sha256 = value_sha256(np.asarray(source["signal"]).tolist())
    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "researcher_input_path": str(INPUT_NOTEBOOK.relative_to(REPO_ROOT)),
        "researcher_input_sha256": file_sha256(INPUT_NOTEBOOK),
        "execution_notebook_path": str(EXECUTION_NOTEBOOK.relative_to(REPO_ROOT)),
        "execution_notebook_sha256": file_sha256(EXECUTION_NOTEBOOK),
        "state_contract_path": str(contract_path.relative_to(REPO_ROOT)),
        "state_contract_sha256": contract_sha256,
        "state_contract_version": contract["version"],
        "crop_signal_sha256": source_sha256,
        "clap_state_sequence_sha256": label_sha256,
        "claspy_version": version("claspy"),
        "featuregraph_version": fg.__version__,
        "python": sys.version,
        "platform": platform.platform(),
    }
    (OUTPUT_ROOT / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n"
    )
    report = f"""# CLaP compiler-backed state-occurrence validation

- State contract SHA-256: `{contract_sha256}`
- CLaP label-sequence SHA-256: `{label_sha256}`
- Observations: {summary['observations']}
- State-occurrence objects: {summary['state_occurrence_objects']}
- Adjacent relations: {summary['adjacent_relations']}

The compiler reproduced the legacy maximal-run occurrence identity exactly. The
object reconstruction matches all 20,700 external CLaP labels, and every frozen
boundary, agreement metric, fragment count, and relation count passed.
"""
    (OUTPUT_ROOT / "validation_report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
