"""Prepare frozen inputs for the blinded BIDMC object-level LLM trial."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

import featuregraph as fg
from experiments.bidmc_llm_capture.native_envelope import (
    native_envelope_objects,
)

SUBJECT = 1
SAMPLING_RATE = 125
DIFF_LAG = 45
EPS = 0.15
MAX_STATE_GAP = 7


def difference_native_objects(
    observations: pd.DataFrame,
) -> pd.DataFrame:
    """Reproduce the original frozen native difference construction."""
    behavior = fg.oscillation.Oscillation(
        signals="respiration",
        group="subject",
        smooth_signal=False,
        diff_lag=DIFF_LAG,
        eps=EPS,
        max_state_gap=MAX_STATE_GAP,
    )
    features = behavior.fit_transform(observations)
    objects = behavior.summarize(
        features,
        signal="respiration",
        include_partial=True,
    ).table.copy()
    objects["period_seconds"] = objects["period"] / SAMPLING_RATE
    objects["full_excursion"] = 2 * objects["amplitude"]
    return objects[
        [
            "oscillation_id",
            "start_index",
            "peak_index",
            "end_index",
            "is_complete",
            "period_seconds",
            "full_excursion",
            "temporal_symmetry",
        ]
    ].rename(columns={"oscillation_id": "featuregraph_object_id"})


def prepare(
    output_directory: Path,
    *,
    construction: str = "envelope",
) -> None:
    """Write raw LLM input and the hidden native comparison table."""
    output_directory.mkdir(parents=True, exist_ok=True)

    observations = fg.datasets.bidmc(subject=SUBJECT)
    raw = observations[["respiration"]].copy()
    raw.insert(0, "sample_index", raw.index)
    raw.insert(1, "time_seconds", raw.index / SAMPLING_RATE)
    raw.to_csv(
        output_directory / "raw_respiration_subject_01.csv",
        index=False,
    )

    if construction == "envelope":
        native, _ = native_envelope_objects(observations)
    elif construction == "difference":
        native = difference_native_objects(observations)
    else:
        raise ValueError(
            "construction must be 'difference' or 'envelope'"
        )
    native.to_csv(
        output_directory / "featuregraph_objects_subject_01.csv",
        index=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--construction",
        choices=("difference", "envelope"),
        default="envelope",
    )
    arguments = parser.parse_args()
    prepare(
        Path(__file__).parent / "generated",
        construction=arguments.construction,
    )
