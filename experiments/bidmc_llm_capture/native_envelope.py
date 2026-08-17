"""Native FeatureGraph construction for the BIDMC respiration envelope."""

from __future__ import annotations

import pandas as pd

import featuregraph as fg

SAMPLING_RATE = 125
ENVELOPE_WINDOW = 100
ENVELOPE_SHIFT = 100
ENVELOPE_SIGNAL = "respiration_envelope"


def center_plateau_boundaries(
    objects: pd.DataFrame,
    features: pd.DataFrame,
    *,
    causal_shift: int = ENVELOPE_SHIFT,
) -> pd.DataFrame:
    """Add exact-flat extrema intervals and canonical midpoint projections.

    The original oscillation construction anchors a peak at the first sample
    of an upper plateau and a trough at the final sample of a lower plateau.
    This optional adapter retains those transition anchors, adds both interval
    edges, and projects each extremum to the floor midpoint. That projection
    matches SciPy's convention for even-length flat peaks.

    ``peak_detection_index`` is the earliest causal sample at which the full
    peak interval and the negatively shifted envelope are both available. It
    is deliberately distinct from the offline-aligned ``peak_index``.
    """
    if causal_shift < 0:
        raise ValueError("causal_shift cannot be negative")

    result = objects.copy()
    boundary_specs = {
        "start_index": "start_trough",
        "peak_index": "peak",
        "end_index": "end_trough",
    }

    for prefix in boundary_specs.values():
        result[f"{prefix}_start_index"] = pd.Series(
            pd.NA,
            index=result.index,
            dtype="Int64",
        )
        result[f"{prefix}_end_index"] = pd.Series(
            pd.NA,
            index=result.index,
            dtype="Int64",
        )

    for boundary, prefix in boundary_specs.items():
        result[f"{prefix}_transition_index"] = result[boundary].astype(
            "Int64"
        )

    for subject, subject_rows in result.groupby("subject", sort=False):
        signal = features.loc[
            features["subject"].eq(subject),
            ENVELOPE_SIGNAL,
        ]
        run_id = signal.ne(signal.shift()).cumsum()
        run_bounds = (
            pd.DataFrame({"sample_index": signal.index, "run_id": run_id})
            .groupby("run_id", sort=False)["sample_index"]
            .agg(["min", "max"])
        )
        sample_to_run = run_id.to_dict()

        for row_index in subject_rows.index:
            for boundary, prefix in boundary_specs.items():
                anchor = result.at[row_index, boundary]
                if pd.isna(anchor):
                    continue
                anchor = int(anchor)
                current_run = sample_to_run[anchor]
                start = int(run_bounds.at[current_run, "min"])
                end = int(run_bounds.at[current_run, "max"])
                result.at[row_index, f"{prefix}_start_index"] = start
                result.at[row_index, f"{prefix}_end_index"] = end
                result.at[row_index, boundary] = start + (end - start) // 2

    result["transition_complete"] = result["is_complete"].astype(bool)
    intervals_present = result[
        [
            "start_trough_end_index",
            "peak_start_index",
            "peak_end_index",
            "end_trough_start_index",
        ]
    ].notna().all(axis=1)
    intervals_ordered = (
        result["start_trough_end_index"].lt(result["peak_start_index"])
        & result["peak_end_index"].lt(result["end_trough_start_index"])
    ).fillna(False)
    result["plateau_boundary_ambiguous"] = (
        intervals_present & ~intervals_ordered
    )
    result["plateau_invalidated_complete"] = (
        result["transition_complete"]
        & result["plateau_boundary_ambiguous"]
    )

    result["period"] = result.groupby("subject", sort=False)[
        "peak_index"
    ].diff()
    rise_duration = result["peak_index"] - result["start_index"]
    fall_duration = result["end_index"] - result["peak_index"]
    duration = result["end_index"] - result["start_index"]
    result["temporal_symmetry"] = (
        1 - (rise_duration - fall_duration).abs() / duration
    ).where(duration > 0)
    result["is_complete"] = (
        result["transition_complete"] & intervals_ordered
    )
    result["peak_detection_index"] = (
        result["peak_end_index"] + causal_shift
    ).astype("Int64")
    result["peak_detection_latency_samples"] = (
        result["peak_detection_index"] - result["peak_index"]
    )
    result["peak_detection_latency_seconds"] = (
        result["peak_detection_latency_samples"] / SAMPLING_RATE
    )
    return result


def centered_plateau_events(
    features: pd.DataFrame,
    event_column: str,
) -> list[int]:
    """Move existing events to exact-flat-run midpoints without adding any."""
    centered: list[int] = []
    for _, group in features.groupby("subject", sort=False):
        signal = group[ENVELOPE_SIGNAL]
        run_id = signal.ne(signal.shift()).cumsum()
        run_bounds = (
            pd.DataFrame({"sample_index": signal.index, "run_id": run_id})
            .groupby("run_id", sort=False)["sample_index"]
            .agg(["min", "max"])
        )
        for anchor in group.index[group[event_column]]:
            current_run = run_id.at[anchor]
            start = int(run_bounds.at[current_run, "min"])
            end = int(run_bounds.at[current_run, "max"])
            centered.append(start + (end - start) // 2)
    return centered


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
    *,
    plateau_midpoints: bool = False,
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
    if plateau_midpoints:
        objects = center_plateau_boundaries(objects, features)

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

    columns = [
        "oscillation_id",
        "start_index",
        "peak_index",
        "end_index",
        "is_complete",
        "period_seconds",
        "full_excursion",
        "temporal_symmetry",
    ]
    if plateau_midpoints:
        columns.extend(
            [
                "transition_complete",
                "plateau_boundary_ambiguous",
                "plateau_invalidated_complete",
                "start_trough_transition_index",
                "start_trough_start_index",
                "start_trough_end_index",
                "peak_transition_index",
                "peak_start_index",
                "peak_end_index",
                "end_trough_transition_index",
                "end_trough_start_index",
                "end_trough_end_index",
                "peak_detection_index",
                "peak_detection_latency_samples",
                "peak_detection_latency_seconds",
            ]
        )
    table = objects[columns].rename(
        columns={"oscillation_id": "featuregraph_object_id"}
    )
    if plateau_midpoints:
        detected_peaks = centered_plateau_events(
            features,
            f"{ENVELOPE_SIGNAL}_peak",
        )
    else:
        detected_peaks = features.index[
            features[f"{ENVELOPE_SIGNAL}_peak"]
        ].astype(int).tolist()
    return table, detected_peaks
