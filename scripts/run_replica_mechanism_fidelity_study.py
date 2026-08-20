"""Compare output equivalence with declared scientific traceability for CLaP."""

from importlib.metadata import version

import numpy as np
import pandas as pd
from claspy.data_loader import load_tssb_dataset
from claspy.state_detection import AgglomerativeCLaPDetection

import featuregraph as fg


def provenance_contract(result) -> pd.Series:
    """Evaluate the declarations needed to identify this CLaP construction."""
    provenance = result.objects[0].provenance
    return pd.Series(
        {
            "dataset_declared": provenance.dataset != "unknown",
            "detector_declared": provenance.parameters["detector"]
            != "external",
            "software_version_declared": provenance.software_version != "unknown",
            "study_specific_contract_declared": provenance.specification_id
            == "clap-crop-state-occurrence-v1",
        },
        name="passed",
    )


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
)

# This surrogate receives the same observations and labels, so it can reproduce
# the same visible output. It deliberately omits the study-specific declarations
# that identify where the labels came from and which contract they implement.
output_only = fg.from_state_sequence(
    clap_states,
    signal=signal,
    group_id="CLAP-CROP",
    signal_name="Crop time series",
    object_type="clap_state_occurrence",
)

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
                ["signal_minimum", "signal_maximum", "signal_mean", "signal_std"]
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

assert equivalence.all()
assert traceability["declared_CLaP"].all()
assert not traceability["output_only"].any()

print("OUTPUT_EQUIVALENCE")
print(equivalence.to_string())
print("\nTRACEABILITY_CONTRACT")
print(traceability.to_string())
print("\nCOUNTS")
print(
    pd.Series(
        {
            "observations": len(signal),
            "state_occurrence_objects": len(declared.objects),
            "adjacent_relations": len(declared.relations),
        }
    ).to_string()
)
