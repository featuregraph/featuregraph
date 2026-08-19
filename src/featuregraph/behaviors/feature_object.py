from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class ObjectStatus(str, Enum):
    CANDIDATE = "candidate"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    AMBIGUOUS = "ambiguous"
    BOUNDARY_TRUNCATED = "boundary_truncated"
    INVALID = "invalid"


@dataclass(frozen=True)
class Boundary:
    name: str
    index: int
    time: float
    time_unit: str
    event_name: str | None = None
    start_index: int | None = None
    end_index: int | None = None

    def __post_init__(self) -> None:
        if self.start_index is not None and self.start_index > self.index:
            raise ValueError("Boundary start_index must not exceed index.")

        if self.end_index is not None and self.index > self.end_index:
            raise ValueError("Boundary index must not exceed end_index.")


@dataclass(frozen=True)
class Measurement:
    name: str
    value: Any
    unit: str | None = None
    definition: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    name: str
    passed: bool
    message: str | None = None


@dataclass(frozen=True)
class Provenance:
    dataset: str
    group_id: Any
    signal: str
    specification_id: str
    software_version: str
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FeatureObject:
    object_id: str
    object_type: str
    group_id: Any
    status: ObjectStatus

    start: Boundary
    end: Boundary
    boundaries: tuple[Boundary, ...] = field(default_factory=tuple)

    measurements: tuple[Measurement, ...] = field(default_factory=tuple)
    validation: tuple[ValidationResult, ...] = field(default_factory=tuple)

    source_start_index: int | None = None
    source_end_index: int | None = None

    component_ids: tuple[str, ...] = field(default_factory=tuple)
    preceding_object_id: str | None = None
    following_object_id: str | None = None

    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if self.start.index > self.end.index:
            raise ValueError("Object start must not occur after object end.")

        if self.start.time > self.end.time:
            raise ValueError("Object start time must not exceed end time.")

        ordered_boundaries = (self.start, *self.boundaries, self.end)
        boundary_indices = [boundary.index for boundary in ordered_boundaries]

        if boundary_indices != sorted(boundary_indices):
            raise ValueError("Object boundaries must be temporally ordered.")

        if self.status is ObjectStatus.COMPLETE:
            failed = [result for result in self.validation if not result.passed]

            if failed:
                raise ValueError(
                    "A complete object cannot contain failed validation results."
                )

    @property
    def duration(self) -> float:
        return self.end.time - self.start.time

    def measurement(self, name: str) -> Measurement:
        matches = [
            measurement
            for measurement in self.measurements
            if measurement.name == name
        ]

        if len(matches) != 1:
            raise KeyError(
                f"Expected exactly one measurement named {name!r}; "
                f"found {len(matches)}."
            )

        return matches[0]

    def explain(self) -> str:
        description = (
            f"{self.object_id} is a {self.status.value} "
            f"{self.object_type} beginning at "
            f"{self.start.time:g} {self.start.time_unit} and ending at "
            f"{self.end.time:g} {self.end.time_unit}. "
            f"Its duration is {self.duration:g} {self.start.time_unit}."
        )

        if self.boundaries:
            phase_text = ", ".join(
                f"{boundary.name} at "
                f"{boundary.time:g} {boundary.time_unit}"
                for boundary in self.boundaries
            )
            description += f" Its internal boundaries are {phase_text}."

        if self.measurements:
            measurement_text = ", ".join(
                (
                    f"{measurement.name}={measurement.value}"
                    + (
                        f" {measurement.unit}"
                        if measurement.unit is not None
                        else ""
                    )
                )
                for measurement in self.measurements
            )
            description += f" Its measurements are {measurement_text}."

        return description

    def to_record(self) -> dict[str, Any]:
        record = {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "group_id": self.group_id,
            "status": self.status.value,
            "start_index": self.start.index,
            "start_time": self.start.time,
            "end_index": self.end.index,
            "end_time": self.end.time,
            "duration": self.duration,
            "source_start_index": self.source_start_index,
            "source_end_index": self.source_end_index,
            "preceding_object_id": self.preceding_object_id,
            "following_object_id": self.following_object_id,
        }

        for measurement in self.measurements:
            record[measurement.name] = measurement.value
            record[f"{measurement.name}_unit"] = measurement.unit

        return record