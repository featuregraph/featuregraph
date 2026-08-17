"""Verify the saved FeatureGraph 0.1.0b1 BIDMC evidence bundle."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

EXPERIMENT_DIRECTORY = Path(__file__).parent
DEFAULT_OUTPUT_DIRECTORY = (
    EXPERIMENT_DIRECTORY / "results" / "envelope_plateau_multi_subject"
)
MANIFEST_PATH = EXPERIMENT_DIRECTORY / "BETA_MANIFEST.json"


def verify_beta_release(
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY,
) -> dict[str, int]:
    """Validate release invariants and return the observed count summary."""
    manifest = json.loads(MANIFEST_PATH.read_text())
    expected = manifest["expected"]

    missing = [
        filename
        for filename in manifest["outputs"]
        if not (output_directory / filename).is_file()
    ]
    if missing:
        raise AssertionError(f"missing beta outputs: {missing}")

    failures = pd.read_csv(output_directory / "failures.csv")
    subjects = pd.read_csv(output_directory / "subject_summary.csv")
    cohort = pd.read_csv(output_directory / "cohort_summary.csv")
    handoff = pd.read_csv(
        output_directory / "detector_discordant_episodes.csv"
    )
    all_subjects = cohort.loc[cohort["cohort"].eq("all_subjects")].iloc[0]

    observed = {
        "subjects": len(subjects),
        "failures": len(failures),
        "detected_peak_events": int(
            subjects["featuregraph_detected_peaks"].sum()
        ),
        "featuregraph_complete_objects": int(
            all_subjects["featuregraph_complete_objects"]
        ),
        "baseline_complete_objects": int(
            all_subjects["baseline_complete_objects"]
        ),
        "matched_objects": int(all_subjects["matched_objects"]),
        "featuregraph_only_objects": int(
            all_subjects["featuregraph_only_objects"]
        ),
        "baseline_only_objects": int(
            all_subjects["baseline_only_objects"]
        ),
        "featuregraph_ambiguous_objects": int(
            all_subjects["featuregraph_ambiguous_objects"]
        ),
        "featuregraph_invalidated_complete_objects": int(
            all_subjects["featuregraph_invalidated_complete_objects"]
        ),
        "excluded_by_both_annotators": int(
            handoff["excluded_by_both_annotators"].sum()
        ),
        "not_excluded_by_both_annotators": int(
            (~handoff["excluded_by_both_annotators"]).sum()
        ),
    }
    if observed != expected:
        raise AssertionError(
            f"beta invariant mismatch: observed={observed}, expected={expected}"
        )

    if not handoff["episode_id"].is_unique:
        raise AssertionError("detector-discordant episode IDs must be unique")
    if not handoff["clinical_interpretation"].eq("unassigned").all():
        raise AssertionError("clinical interpretation must remain unassigned")
    if not handoff["construction_version"].eq(
        manifest["construction"]["version"]
    ).all():
        raise AssertionError("construction version differs from manifest")
    if not handoff["discordance_type"].eq("featuregraph_only").all():
        raise AssertionError("handoff contains an unexpected discordance type")
    if not handoff["temporal_pattern"].isin(
        {"isolated", "burst"}
    ).all():
        raise AssertionError("handoff contains an unexpected temporal label")

    return observed


if __name__ == "__main__":
    counts = verify_beta_release()
    print("FeatureGraph 0.1.0b1 BIDMC evidence verified:")
    for key, value in counts.items():
        print(f"  {key}: {value}")
