from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd


_DEFAULT_SEGMENTS: tuple[dict[str, float | int | str], ...] = (
    {"state": "stable", "target": 1.0, "duration": 40},
    {"state": "falling", "target": 0.2, "duration": 8},
    {"state": "stable", "target": 0.2, "duration": 20},
    {"state": "rising", "target": 1.0, "duration": 8},
    {"state": "stable", "target": 1.0, "duration": 35},
    {"state": "falling", "target": 0.2, "duration": 12},
    {"state": "stable", "target": 0.2, "duration": 45},
    {"state": "rising", "target": 1.0, "duration": 12},
    {"state": "stable", "target": 1.0, "duration": 30},
)


def pulse(
    segments: Iterable[Mapping[str, float | int | str]] | None = None,
    *,
    initial_value: float = 1.0,
    sample_interval: float = 1.0,
    start_time: float = 0.0,
    signal_name: str = "signal",
) -> pd.DataFrame:
    """Generate a deterministic piecewise-linear pulse signal.

    Each segment is a mapping with three required fields:

    ``state``
        One of ``"rising"``, ``"falling"``, or ``"stable"``.
    ``target``
        The value reached at the final sample of the segment. Stable segments
        must target the current value.
    ``duration``
        The number of samples generated for the segment.

    Moving segments exclude their initial boundary value and include their
    target value. This prevents duplicate samples where adjacent segments meet
    while preserving exact, deterministic boundaries.

    Parameters
    ----------
    segments
        Ordered segment specifications. When omitted, a neutral step-and-hold
        example containing rising, falling, and stable episodes is generated.
    initial_value
        Signal value immediately before the first generated sample.
    sample_interval
        Time between consecutive samples. Must be positive.
    start_time
        Time assigned to the first generated sample.
    signal_name
        Name of the generated signal column.

    Returns
    -------
    pandas.DataFrame
        Columns are ``sample``, ``time``, the requested signal column,
        ``true_state``, and ``true_segment_id``.
    """
    if sample_interval <= 0:
        raise ValueError("sample_interval must be positive")
    if not signal_name:
        raise ValueError("signal_name must be a non-empty string")

    specifications = tuple(_DEFAULT_SEGMENTS if segments is None else segments)
    if not specifications:
        raise ValueError("segments must contain at least one segment")

    values: list[np.ndarray] = []
    states: list[str] = []
    segment_ids: list[int] = []
    current = float(initial_value)

    for segment_id, specification in enumerate(specifications):
        missing = {"state", "target", "duration"} - set(specification)
        if missing:
            missing_fields = ", ".join(sorted(missing))
            raise ValueError(f"segment {segment_id} is missing: {missing_fields}")

        state = str(specification["state"])
        target = float(specification["target"])
        duration = int(specification["duration"])

        if state not in {"rising", "falling", "stable"}:
            raise ValueError(
                f"segment {segment_id} has invalid state {state!r}; "
                "expected 'rising', 'falling', or 'stable'"
            )
        if duration <= 0:
            raise ValueError(f"segment {segment_id} duration must be positive")

        if state == "rising" and target <= current:
            raise ValueError(
                f"segment {segment_id} is rising but target {target} "
                f"is not greater than current value {current}"
            )
        if state == "falling" and target >= current:
            raise ValueError(
                f"segment {segment_id} is falling but target {target} "
                f"is not less than current value {current}"
            )
        if state == "stable" and not np.isclose(target, current):
            raise ValueError(
                f"segment {segment_id} is stable but target {target} "
                f"does not equal current value {current}"
            )

        if state == "stable":
            segment_values = np.full(duration, current, dtype=float)
        else:
            segment_values = np.linspace(
                current,
                target,
                num=duration + 1,
                dtype=float,
            )[1:]

        values.append(segment_values)
        states.extend([state] * duration)
        segment_ids.extend([segment_id] * duration)
        current = target

    signal = np.concatenate(values)
    sample = np.arange(signal.size, dtype=int)
    time = start_time + sample * sample_interval

    return pd.DataFrame(
        {
            "sample": sample,
            "time": time,
            signal_name: signal,
            "true_state": states,
            "true_segment_id": segment_ids,
        }
    )
