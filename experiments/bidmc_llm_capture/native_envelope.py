"""Native FeatureGraph construction for the BIDMC respiration envelope."""

from __future__ import annotations

import pandas as pd

import featuregraph as fg

SAMPLING_RATE = 125
ENVELOPE_WINDOW = 100
ENVELOPE_SHIFT = 100
ENVELOPE_SIGNAL = "respiration_envelope"


def add_respiration_envelope(
    observations: pd.DataFrame,
    *,
    window: int = ENVELOPE_WINDOW,
    shift: int = ENVELOPE_SHIFT,
) -> pd.DataFrame:
    """Add the grouped rolling-maximum/rolling-mean envelope.

    The negative shift aligns the offline envelope with the observations that
    produced it. A causal implementation computes the same value ``shift``
    samples later and records separate event and detection times.
    """
    if window < 1:
        raise ValueError("window must be at least 1")
    if shift < 0:
        raise ValueError("shift cannot be negative")

    required = {"subject", "respiration"}
    missing = required.difference(observations.columns)
    if missing:
        raise ValueError(
            "observations must contain subject and respiration columns"
        )

    result = observations.copy()
    result["respiration_raw"] = result["respiration"]
    result[ENVELOPE_SIGNAL] = (
        result.groupby("subject", sort=False)["respiration"]
        .transform(
            lambda signal: (
                signal.rolling(window, min_periods=window)
                .max()
                .rolling(window, min_periods=window)
                .mean()
                .shift(-shift)
            )
        )
    )
    return result


def native_envelope_objects(
    observations: pd.DataFrame,
) -> tuple[pd.DataFrame, list[int]]:
    """Construct BIDMC objects from envelope transitions and raw values."""
    prepared = add_respiration_envelope(observations)
    prepared = prepared.dropna(subset=[ENVELOPE_SIGNAL]).copy()

    behavior = fg.oscillation.Oscillation(
        signals=ENVELOPE_SIGNAL,
        group="subject",
        smooth_signal=False,
        diff_lag=1,
        eps=0.0,
        max_state_gap=0,
    )
    features = behavior.fit_transform(prepared)
    objects = behavior.summarize(
        features,
        signal=ENVELOPE_SIGNAL,
        include_partial=True,
    ).table.copy()

    object_id = f"{ENVELOPE_SIGNAL}_wave_id"
    raw_ranges = (
        features.groupby(
            ["subject", object_id],
            sort=False,
        )["respiration_raw"]
        .agg(raw_minimum="min", raw_maximum="max")
        .reset_index()
        .rename(columns={object_id: "oscillation_id"})
    )
    objects = objects.merge(
        raw_ranges,
        on=["subject", "oscillation_id"],
        how="left",
        validate="one_to_one",
    )
    objects["period_seconds"] = objects["period"] / SAMPLING_RATE
    objects["full_excursion"] = (
        objects["raw_maximum"] - objects["raw_minimum"]
    )

    table = objects[
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
    detected_peaks = features.index[
        features[f"{ENVELOPE_SIGNAL}_peak"]
    ].astype(int).tolist()
    return table, detected_peaks
