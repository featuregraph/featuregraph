"""Materialize categorical state sequences as bounded behavioral objects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from featuregraph.behaviors.feature_object import (
    Boundary,
    FeatureObject,
    Measurement,
    ObjectStatus,
    Provenance,
    ValidationResult,
)
from featuregraph.contracts.state_contract import compile_states
from featuregraph.operators.events import enter_label, event_id, exit_label


@dataclass(frozen=True)
class StateOccurrenceResult:
    """Observation, object, and relation layers for one state sequence."""

    observations: pd.DataFrame
    objects: tuple[FeatureObject, ...]
    relations: pd.DataFrame

    def object_table(self) -> pd.DataFrame:
        """Return one record per occurrence object."""
        return pd.DataFrame(obj.to_record() for obj in self.objects)

    def reconstruct_states(self) -> np.ndarray:
        """Reconstruct the sample-level labels from object measurements."""
        parts = []
        for obj in self.objects:
            label = obj.measurement("state_label").value
            count = int(obj.measurement("sample_count").value)
            parts.append(np.repeat(label, count))
        return np.concatenate(parts) if parts else np.asarray([])


def _boundary_times(times: np.ndarray) -> np.ndarray:
    if len(times) == 1:
        return np.asarray([times[0], times[0] + 1.0], dtype=float)
    deltas = np.diff(times)
    if np.any(~np.isfinite(deltas)) or np.any(deltas <= 0):
        raise ValueError("times must be finite and strictly increasing.")
    return np.r_[times, times[-1] + deltas[-1]]


def from_state_sequence(
    states: Sequence[Any],
    *,
    signal: Sequence[float] | None = None,
    times: Sequence[float] | None = None,
    group_id: Any = "series-0",
    dataset: str = "unknown",
    signal_name: str = "signal",
    signal_unit: str | None = None,
    detector: str = "external",
    specification_id: str = "categorical-state-occurrence-v1",
    software_version: str = "unknown",
    time_unit: str = "sample",
    object_type: str = "state_occurrence",
    state_contract: Mapping[str, Any] | None = None,
) -> StateOccurrenceResult:
    """Convert labels into one object per maximal contiguous label run.

    The detector remains outside FeatureGraph. No labels are smoothed, merged,
    split, or relabelled. Intervals use half-open sample boundaries ``[s, e)``.
    The first and final objects are retained as boundary-truncated fragments.
    """
    states_array = np.asarray(states)
    if states_array.ndim != 1 or len(states_array) == 0:
        raise ValueError("states must be a non-empty one-dimensional sequence.")
    if pd.isna(states_array).any():
        raise ValueError("states must not contain missing labels.")

    n_samples = len(states_array)
    signal_array = None if signal is None else np.asarray(signal, dtype=float)
    if signal_array is not None and (
        signal_array.ndim != 1 or len(signal_array) != n_samples
    ):
        raise ValueError("signal must be one-dimensional and align with states.")

    if times is None:
        sample_times = np.arange(n_samples, dtype=float)
        boundary_times = np.arange(n_samples + 1, dtype=float)
    else:
        sample_times = np.asarray(times, dtype=float)
        if sample_times.ndim != 1 or len(sample_times) != n_samples:
            raise ValueError("times must be one-dimensional and align with states.")
        boundary_times = _boundary_times(sample_times)

    observations = pd.DataFrame(
        {
            "sample_index": np.arange(n_samples, dtype=int),
            "time": sample_times,
            "state_label": states_array.copy(),
        }
    )
    if signal_array is not None:
        observations["signal_raw"] = signal_array.copy()
    if state_contract is None:
        state_contract = {
            "version": "state-contract-v1",
            "state_column": "state_label",
            "events": {},
            "boundary_policy": {
                "include_first_entry": True,
                "include_last_exit": True,
            },
        }
    compiled = compile_states(observations, state_contract)
    if not compiled.observations["state"].equals(observations["state_label"]):
        raise AssertionError("The state contract did not preserve external labels.")
    observations["enter_state_occurrence"] = enter_label(observations["state_label"])
    observations["exit_state_occurrence"] = exit_label(observations["state_label"])
    observations["occurrence_id"] = compiled.observations[
        "state_occurrence_id"
    ].astype(int)
    legacy_occurrence_id = (
        event_id(observations, "enter_state_occurrence").astype(int) - 1
    )
    if not observations["occurrence_id"].equals(legacy_occurrence_id):
        raise AssertionError("Compiled occurrence identity changed legacy semantics.")

    grouped = observations.groupby("occurrence_id", sort=True)
    summary = grouped.agg(
        state_label=("state_label", "first"),
        unique_state_count=("state_label", "nunique"),
        start_index=("sample_index", "min"),
        source_end_index=("sample_index", "max"),
        sample_count=("sample_index", "size"),
        enter_count=("enter_state_occurrence", "sum"),
        exit_count=("exit_state_occurrence", "sum"),
    ).reset_index()
    if signal_array is not None:
        signal_summary = (
            grouped["signal_raw"]
            .agg(
                signal_minimum="min",
                signal_maximum="max",
                signal_mean="mean",
                signal_std=lambda values: values.std(ddof=0),
            )
            .reset_index()
        )
        summary = summary.merge(signal_summary, on="occurrence_id", validate="1:1")

    provenance = Provenance(
        dataset=dataset,
        group_id=group_id,
        signal=signal_name,
        specification_id=specification_id,
        software_version=software_version,
        parameters={
            "detector": detector,
            "interval_convention": "half-open",
            "state_contract_version": compiled.contract["version"],
        },
    )

    object_count = len(summary)
    objects = []
    for position, row in enumerate(summary.itertuples(index=False)):
        start_index = int(row.start_index)
        end_index = int(row.source_end_index) + 1
        boundary_fragment = position in (0, object_count - 1)
        measurements = [
            Measurement(
                "state_label",
                row.state_label,
                definition="External detector label",
            ),
            Measurement("sample_count", int(row.sample_count), "samples"),
        ]
        if signal_array is not None:
            measurements.extend(
                [
                    Measurement(
                        "signal_minimum", float(row.signal_minimum), signal_unit
                    ),
                    Measurement(
                        "signal_maximum", float(row.signal_maximum), signal_unit
                    ),
                    Measurement("signal_mean", float(row.signal_mean), signal_unit),
                    Measurement("signal_std", float(row.signal_std), signal_unit),
                ]
            )
        object_id = f"{group_id}-O{int(row.occurrence_id):03d}"
        objects.append(
            FeatureObject(
                object_id=object_id,
                object_type=object_type,
                group_id=group_id,
                status=(
                    ObjectStatus.BOUNDARY_TRUNCATED
                    if boundary_fragment
                    else ObjectStatus.COMPLETE
                ),
                start=Boundary(
                    name="start",
                    index=start_index,
                    time=float(boundary_times[start_index]),
                    time_unit=time_unit,
                    event_name="enter_state_occurrence",
                ),
                end=Boundary(
                    name="end_exclusive",
                    index=end_index,
                    time=float(boundary_times[end_index]),
                    time_unit=time_unit,
                    event_name="exit_state_occurrence",
                ),
                measurements=tuple(measurements),
                validation=(
                    ValidationResult(
                        "constant_state", int(row.unique_state_count) == 1
                    ),
                    ValidationResult("one_entry", int(row.enter_count) == 1),
                    ValidationResult("one_exit", int(row.exit_count) == 1),
                ),
                source_start_index=start_index,
                source_end_index=int(row.source_end_index),
                preceding_object_id=(
                    f"{group_id}-O{position - 1:03d}" if position > 0 else None
                ),
                following_object_id=(
                    f"{group_id}-O{position + 1:03d}"
                    if position + 1 < object_count
                    else None
                ),
                provenance=provenance,
            )
        )

    relations = pd.DataFrame(
        [
            {
                "relation": "precedes",
                "source_object_id": left.object_id,
                "target_object_id": right.object_id,
                "source_state": left.measurement("state_label").value,
                "target_state": right.measurement("state_label").value,
                "boundary_index": right.start.index,
            }
            for left, right in zip(objects, objects[1:], strict=False)
        ],
        columns=[
            "relation",
            "source_object_id",
            "target_object_id",
            "source_state",
            "target_state",
            "boundary_index",
        ],
    )

    result = StateOccurrenceResult(observations, tuple(objects), relations)
    if not np.array_equal(result.reconstruct_states(), states_array):
        raise AssertionError(
            "Occurrence objects did not reconstruct the state sequence."
        )
    return result
