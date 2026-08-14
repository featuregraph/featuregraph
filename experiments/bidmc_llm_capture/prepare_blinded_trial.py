"""Prepare frozen inputs for the blinded BIDMC object-level LLM trial."""

from __future__ import annotations

from pathlib import Path

import featuregraph as fg


SUBJECT = 1
SAMPLING_RATE = 125
DIFF_LAG = 45
EPS = 0.15
MAX_STATE_GAP = 7


def prepare(output_directory: Path) -> None:
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
    native = objects[
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
    native.to_csv(
        output_directory / "featuregraph_objects_subject_01.csv",
        index=False,
    )


if __name__ == "__main__":
    prepare(Path(__file__).parent / "generated")
