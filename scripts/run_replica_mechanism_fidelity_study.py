"""Compare output equivalence with declared scientific traceability for CLaP."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from claspy.data_loader import load_tssb_dataset
from claspy.state_detection import AgglomerativeCLaPDetection

import featuregraph as fg
from featuregraph.contracts.study_workflow import (
    declarative_values,
    file_sha256,
    notebook_sources,
    value_sha256,
    write_json_artifact,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAP_INPUT_NOTEBOOK = (
    REPO_ROOT / "notebooks" / "researcher_input" / "clap_researcher_input.ipynb"
)
OUTPUT_ROOT = REPO_ROOT / "outputs" / "replica_mechanism_fidelity"
EXPECTED_LABEL_SHA256 = (
    "f3b8f863b95801db39e32bf611c1bfba6e4585870b0df627af509da59f610b9b"
)


def provenance_contract(result) -> pd.Series:
    """Evaluate declarations needed to identify this CLaP construction."""
    provenance = result.objects[0].provenance
    return pd.Series(
        {
            "dataset_declared": provenance.dataset != "unknown",
            "detector_declared": provenance.parameters["detector"] != "external",
            "software_version_declared": provenance.software_version != "unknown",
            "study_specific_contract_declared": provenance.specification_id
            == "clap-crop-state-occurrence-v1",
        },
        name="passed",
    )


def build_results(state_contract: dict[str, object]):
    source = load_tssb_dataset(names=("Crop",)).iloc[0]
    _, _, _, _, signal = source
    signal = np.asarray(signal, dtype=float)
    detector = AgglomerativeCLaPDetection()
    clap_states = np.asarray(detector.fit_predict(signal))

    declared = fg.from_state_sequence(
        clap_states,
        signal=signal,
        group_id="CLAP-CROP",
        dataset="TSSB Crop",
        signal_name="Crop time series",
        detector="claspy.state_detection.AgglomerativeCLaPDetection",
        specification_id="clap-crop-state-occurrence-v1",
        software_version=f"claspy-{version('claspy')}",
        object_type="clap_state_occurrence",
        state_contract=state_contract,
    )

    # This surrogate receives the same observations and labels, so it can
    # reproduce the same visible output. It deliberately omits the declarations
    # that identify where the labels came from and which study they implement.
    output_only = fg.from_state_sequence(
        clap_states,
        signal=signal,
        group_id="CLAP-CROP",
        signal_name="Crop time series",
        object_type="clap_state_occurrence",
        state_contract=state_contract,
    )
    return signal, clap_states, declared, output_only


def compare_results(declared, output_only) -> tuple[pd.Series, pd.DataFrame]:
    declared_objects = declared.object_table()
    output_only_objects = output_only.object_table()
    equivalence = pd.Series(
        {
            "sample_labels_equal": np.array_equal(
                declared.reconstruct_states(), output_only.reconstruct_states()
            ),
            "object_boundaries_equal": declared_objects[
                ["start_index", "end_index", "state_label", "sample_count"]
            ].equals(
                output_only_objects[
                    ["start_index", "end_index", "state_label", "sample_count"]
                ]
            ),
            "relations_equal": declared.relations.equals(output_only.relations),
            "signal_measurements_equal": declared_objects[
                ["signal_minimum", "signal_maximum", "signal_mean", "signal_std"]
            ].equals(
                output_only_objects[
                    [
                        "signal_minimum",
                        "signal_maximum",
                        "signal_mean",
                        "signal_std",
                    ]
                ]
            ),
        },
        name="equal",
    )
    traceability = pd.concat(
        {
            "declared_CLaP": provenance_contract(declared),
            "output_only": provenance_contract(output_only),
        },
        axis=1,
    )
    return equivalence, traceability


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    input_source = "\n\n".join(notebook_sources(CLAP_INPUT_NOTEBOOK))
    contract = declarative_values(input_source, CLAP_INPUT_NOTEBOOK)["state_contract"]
    contract_path = OUTPUT_ROOT / "state_contract.json"
    contract_sha256 = write_json_artifact(contract_path, contract)

    signal, clap_states, declared, output_only = build_results(contract)
    equivalence, traceability = compare_results(declared, output_only)
    label_sha256 = value_sha256(clap_states.tolist())
    assert label_sha256 == EXPECTED_LABEL_SHA256
    assert len(signal) == 20_700
    assert len(declared.objects) == 9
    assert len(declared.relations) == 8
    assert equivalence.all()
    assert traceability["declared_CLaP"].all()
    assert not traceability["output_only"].any()

    equivalence.to_csv(OUTPUT_ROOT / "output_equivalence.csv", header=True)
    traceability.to_csv(OUTPUT_ROOT / "traceability_contract.csv")
    declared.object_table().to_csv(
        OUTPUT_ROOT / "declared_objects.csv", index=False
    )
    output_only.object_table().to_csv(
        OUTPUT_ROOT / "output_only_objects.csv", index=False
    )
    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "researcher_input_path": str(CLAP_INPUT_NOTEBOOK.relative_to(REPO_ROOT)),
        "researcher_input_sha256": file_sha256(CLAP_INPUT_NOTEBOOK),
        "state_contract_path": str(contract_path.relative_to(REPO_ROOT)),
        "state_contract_sha256": contract_sha256,
        "clap_state_sequence_sha256": label_sha256,
        "claspy_version": version("claspy"),
        "featuregraph_version": fg.__version__,
        "python": sys.version,
        "platform": platform.platform(),
    }
    (OUTPUT_ROOT / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n"
    )
    declared_passed = int(traceability["declared_CLaP"].sum())
    output_only_passed = int(traceability["output_only"].sum())
    report = f"""# Replica mechanism-fidelity validation

- State contract SHA-256: `{contract_sha256}`
- CLaP label-sequence SHA-256: `{label_sha256}`
- Output-equivalence checks passed: {int(equivalence.sum())}/{len(equivalence)}
- Declared traceability checks passed: {declared_passed}/{len(traceability)}
- Output-only traceability checks passed: {output_only_passed}/{len(traceability)}

Both constructions are exactly equal in labels, object boundaries, relations,
and signal measurements. Only the declared construction identifies its dataset,
detector, software version, and study-specific specification. Exact output
agreement therefore still does not establish scientific mechanism fidelity.
"""
    (OUTPUT_ROOT / "validation_report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
