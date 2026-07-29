from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd


_DEFAULT_PHASES: tuple[dict[str, float | int | str], ...] = (
    {"state": "stable", "flow_rate": 0.0, "duration": 20},
    {"state": "filling", "flow_rate": 2.0, "duration": 30},
    {"state": "stable", "flow_rate": 0.0, "duration": 15},
    {"state": "filling", "flow_rate": 0.8, "duration": 40},
    {"state": "stable", "flow_rate": 0.0, "duration": 10},
    {"state": "filling", "flow_rate": 1.5, "duration": 25},
    {"state": "stable", "flow_rate": 0.0, "duration": 20},
)


def tank_fill(
    phases: Iterable[Mapping[str, float | int | str]] | None = None,
    *,
    initial_volume: float = 10.0,
    sample_interval: float = 1.0,
    start_time: float = 0.0,
    capacity: float | None = None,
) -> pd.DataFrame:
    """Generate a deterministic tank-filling time series.

    Each phase is a mapping with three required fields:

    ``state``
        Either ``"filling"`` or ``"stable"``.
    ``flow_rate``
        Water added per unit time. Filling phases require a positive value;
        stable phases require zero.
    ``duration``
        Number of generated samples in the phase.

    Volume is updated once per sample according to
    ``volume[t] = volume[t - 1] + flow_rate * sample_interval``.

    Parameters
    ----------
    phases
        Ordered phase specifications. When omitted, a sequence of filling
        periods at different rates separated by stable periods is generated.
    initial_volume
        Volume immediately before the first generated sample.
    sample_interval
        Time between consecutive samples. Must be positive.
    start_time
        Time assigned to the first generated sample.
    capacity
        Optional maximum tank volume. Generation fails if a phase would exceed
        this value.

    Returns
    -------
    pandas.DataFrame
        Columns are ``sample``, ``time``, ``volume``, ``flow_rate``,
        ``true_state``, and ``true_segment_id``.
    """
    if initial_volume < 0:
        raise ValueError("initial_volume must be nonnegative")
    if sample_interval <= 0:
        raise ValueError("sample_interval must be positive")
    if capacity is not None and capacity <= 0:
        raise ValueError("capacity must be positive")
    if capacity is not None and initial_volume > capacity:
        raise ValueError("initial_volume cannot exceed capacity")

    specifications = tuple(_DEFAULT_PHASES if phases is None else phases)
    if not specifications:
        raise ValueError("phases must contain at least one phase")

    volumes: list[float] = []
    rates: list[float] = []
    states: list[str] = []
    segment_ids: list[int] = []
    current_volume = float(initial_volume)

    for segment_id, specification in enumerate(specifications):
        missing = {"state", "flow_rate", "duration"} - set(specification)
        if missing:
            missing_fields = ", ".join(sorted(missing))
            raise ValueError(f"phase {segment_id} is missing: {missing_fields}")

        state = str(specification["state"])
        flow_rate = float(specification["flow_rate"])
        duration = int(specification["duration"])

        if state not in {"filling", "stable"}:
            raise ValueError(
                f"phase {segment_id} has invalid state {state!r}; "
                "expected 'filling' or 'stable'"
            )
        if duration <= 0:
            raise ValueError(f"phase {segment_id} duration must be positive")
        if state == "filling" and flow_rate <= 0:
            raise ValueError(
                f"phase {segment_id} is filling but flow_rate is not positive"
            )
        if state == "stable" and not np.isclose(flow_rate, 0.0):
            raise ValueError(
                f"phase {segment_id} is stable but flow_rate is not zero"
            )

        for _ in range(duration):
            current_volume += flow_rate * sample_interval
            if capacity is not None and current_volume > capacity:
                raise ValueError(
                    f"phase {segment_id} exceeds tank capacity {capacity}"
                )
            volumes.append(current_volume)
            rates.append(flow_rate)
            states.append(state)
            segment_ids.append(segment_id)

    sample = np.arange(len(volumes), dtype=int)
    time = start_time + sample * sample_interval

    return pd.DataFrame(
        {
            "sample": sample,
            "time": time,
            "volume": volumes,
            "flow_rate": rates,
            "true_state": states,
            "true_segment_id": segment_ids,
        }
    )
