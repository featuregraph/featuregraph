"""Measures over compiled occurrences that need no knowledge of the signal.

Everything here reads the observations :func:`featuregraph.compile_states`
returns and asks about shape alone: how long runs last, how a rise compares
with the fall that follows it, and whether those quantities change across a
record. None of it knows what the column was, and none of it needs to.

Positions are row positions within a group, so a measure can say *where* in
a record something happened without knowing the time base.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

__all__ = ["occurrences", "rise_fall_asymmetry", "occurrence_drift"]


def _group_columns(group_by: str | Sequence[str] | None) -> list[str]:
    if group_by is None:
        return []
    if isinstance(group_by, str):
        return [group_by]
    return list(group_by)


def _require_compiled(observations: pd.DataFrame) -> None:
    missing = [c for c in ("state", "state_occurrence_id") if c not in observations]
    if missing:
        raise ValueError(
            f"Observations must come from compile_states; missing columns {missing}."
        )


def occurrences(
    observations: pd.DataFrame, *, group_by: str | Sequence[str] | None = None
) -> pd.DataFrame:
    """One row per occurrence: its state, where it starts and ends, how long it is.

    ``start_position`` and ``end_position`` count rows within the group, so
    an occurrence in a record compiled under ``missing_policy: "exclude"``
    still sits where it sat in the record. ``sample_count`` counts only the
    rows the occurrence actually holds. Rows outside the partition, where
    ``state_valid`` is ``False``, belong to no occurrence.
    """
    _require_compiled(observations)
    groups = _group_columns(group_by)
    frame = observations[[*groups, "state", "state_occurrence_id"]].copy()
    frame["position"] = (
        frame.groupby(groups, sort=False).cumcount()
        if groups
        else np.arange(len(frame))
    )
    if "state_valid" in observations:
        frame = frame[observations["state_valid"].to_numpy()]
    frame["state_occurrence_id"] = frame["state_occurrence_id"].astype("int64")

    keys = [*groups, "state_occurrence_id"]
    table = (
        frame.groupby(keys, sort=False, dropna=False)
        .agg(
            state=("state", "first"),
            start_position=("position", "min"),
            end_position=("position", "max"),
            sample_count=("position", "size"),
        )
        .reset_index()
    )
    return table


def rise_fall_asymmetry(
    observations: pd.DataFrame,
    *,
    rising: str = "rising",
    falling: str = "falling",
    group_by: str | Sequence[str] | None = None,
) -> pd.DataFrame:
    """How each rise compares with the fall that immediately follows it.

    One row per ``rising`` occurrence. When the next occurrence in the group
    is ``falling``, ``asymmetry`` is the rising share of the pair,
    ``rising_samples / (rising_samples + falling_samples)``: 0.5 is symmetric,
    above 0.5 is a slow rise and a fast fall, below is the reverse. When the
    next occurrence is anything else, or there is none, the row stays with
    ``paired`` set to ``False`` and no asymmetry, so an unpaired rise is
    reported rather than dropped.
    """
    table = occurrences(observations, group_by=group_by)
    groups = _group_columns(group_by)
    grouped = table.groupby(groups, sort=False) if groups else table
    table = table.assign(
        next_state=grouped["state"].shift(-1),
        next_samples=grouped["sample_count"].shift(-1),
        next_occurrence_id=grouped["state_occurrence_id"].shift(-1),
    )
    rises = table[table["state"] == rising].copy()
    paired = rises["next_state"] == falling
    result = pd.DataFrame(
        {
            **{column: rises[column].to_numpy() for column in groups},
            "rising_occurrence_id": rises["state_occurrence_id"].to_numpy(),
            "start_position": rises["start_position"].to_numpy(),
            "rising_samples": rises["sample_count"].to_numpy(),
            "paired": paired.to_numpy(),
            "falling_occurrence_id": rises["next_occurrence_id"]
            .where(paired)
            .astype("Int64")
            .to_numpy(),
            "falling_samples": rises["next_samples"]
            .where(paired)
            .astype("Int64")
            .to_numpy(),
        }
    )
    total = result["rising_samples"] + result["falling_samples"].astype("float64")
    result["asymmetry"] = (result["rising_samples"] / total).where(result["paired"])
    return result.reset_index(drop=True)


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or np.ptp(x) == 0:
        return float("nan")
    x_centered = x - x.mean()
    return float((x_centered * (y - y.mean())).sum() / (x_centered**2).sum())


def occurrence_drift(
    observations: pd.DataFrame,
    *,
    group_by: str | Sequence[str] | None = None,
    measure: str = "sample_count",
) -> pd.DataFrame:
    """Whether a per-occurrence measure changes across a record.

    For each group and state, fits a least-squares line of ``measure``
    against where the occurrence starts, with position normalised to ``[0, 1]``
    over the group. ``slope`` is therefore the fitted change in the measure
    from the start of the record to its end, in the measure's own units.
    ``first_half_median`` and ``second_half_median`` split the occurrences by
    position for a reading that does not depend on the fit. Fewer than two
    occurrences give no slope.
    """
    table = occurrences(observations, group_by=group_by)
    groups = _group_columns(group_by)
    if measure not in table:
        raise ValueError(f"Unknown occurrence measure {measure!r}.")

    lengths = (
        observations.groupby(groups, sort=False).size()
        if groups
        else pd.Series({(): len(observations)})
    )
    rows = []
    keys = [*groups, "state"]
    for key, part in table.groupby(keys, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        group_key = key[:-1]
        length = (
            int(lengths.loc[group_key if len(group_key) > 1 else group_key[0]])
            if groups
            else len(observations)
        )
        x = part["start_position"].to_numpy(dtype=float) / max(length - 1, 1)
        y = part[measure].to_numpy(dtype=float)
        first = y[x < 0.5]
        second = y[x >= 0.5]
        rows.append(
            {
                **dict(zip(groups, group_key, strict=True)),
                "state": key[-1],
                "occurrences": len(part),
                "slope": _slope(x, y),
                "first_half_median": float(np.median(first)) if len(first) else np.nan,
                "second_half_median": float(np.median(second))
                if len(second)
                else np.nan,
            }
        )
    return pd.DataFrame(rows)
