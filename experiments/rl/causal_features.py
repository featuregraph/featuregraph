"""Causal, sample-aligned behavioral features for online RL experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

Representation = Literal["raw", "raw_history", "featuregraph", "augmented"]

FEATURE_NAMES = (
    "direction",
    "reversal",
    "phase_elapsed",
    "displacement_from_extremum",
    "running_amplitude",
    "running_signed_area",
    "previous_phase_amplitude",
    "previous_phase_duration",
    "completed_phases",
    "previous_cycle_amplitude",
    "previous_cycle_duration",
    "completed_cycles",
)


@dataclass
class _Extremum:
    kind: int
    step: int
    value: float


class CausalOscillationEncoder:
    """Construct online oscillation-phase features without future leakage.

    A phase ends only after a direction reversal is observed. Completed-cycle
    measurements update only when two extrema of the same kind have been
    observed with the opposite extremum between them.
    """

    def __init__(self, *, epsilon: float = 0.0) -> None:
        if epsilon < 0:
            raise ValueError("epsilon must be non-negative")
        self.epsilon = float(epsilon)
        self._initialized = False

    @property
    def feature_names(self) -> tuple[str, ...]:
        return FEATURE_NAMES

    def reset(self, signal: float) -> np.ndarray:
        """Start an independent episode and return its initial feature row."""
        value = _finite_scalar(signal)
        self._initialized = True
        self._step = 0
        self._previous_value = value
        self._direction = 0
        self._phase_start_step = 0
        self._phase_start_value = value
        self._running_signed_area = 0.0
        self._previous_phase_amplitude = 0.0
        self._previous_phase_duration = 0.0
        self._completed_phases = 0
        self._previous_cycle_amplitude = 0.0
        self._previous_cycle_duration = 0.0
        self._completed_cycles = 0
        self._extrema: list[_Extremum] = []
        return self._features(value, reversal=False)

    def update(self, signal: float) -> np.ndarray:
        """Consume one new sample and return features available at that sample."""
        if not self._initialized:
            raise RuntimeError("reset must be called before update")

        value = _finite_scalar(signal)
        self._step += 1
        delta = value - self._previous_value
        if delta > self.epsilon:
            new_direction = 1
        elif delta < -self.epsilon:
            new_direction = -1
        else:
            new_direction = 0
        reversal = bool(
            new_direction != 0
            and self._direction != 0
            and new_direction != self._direction
        )

        if reversal:
            extremum_kind = self._direction
            extremum = _Extremum(
                kind=extremum_kind,
                step=self._step - 1,
                value=self._previous_value,
            )
            self._previous_phase_amplitude = abs(
                extremum.value - self._phase_start_value
            )
            self._previous_phase_duration = float(
                extremum.step - self._phase_start_step
            )
            self._completed_phases += 1
            self._extrema.append(extremum)
            self._update_completed_cycle()
            self._phase_start_step = extremum.step
            self._phase_start_value = extremum.value
            self._running_signed_area = 0.0

        if new_direction != 0:
            self._direction = new_direction

        self._running_signed_area += value - self._phase_start_value
        self._previous_value = value
        return self._features(value, reversal=reversal)

    def _update_completed_cycle(self) -> None:
        if len(self._extrema) < 3:
            return
        start, middle, end = self._extrema[-3:]
        if start.kind != end.kind or start.kind == middle.kind:
            return
        self._previous_cycle_duration = float(end.step - start.step)
        self._previous_cycle_amplitude = abs(middle.value - start.value)
        self._completed_cycles += 1

    def _features(self, value: float, *, reversal: bool) -> np.ndarray:
        displacement = value - self._phase_start_value
        return np.asarray(
            [
                self._direction,
                float(reversal),
                self._step - self._phase_start_step,
                displacement,
                abs(displacement),
                self._running_signed_area,
                self._previous_phase_amplitude,
                self._previous_phase_duration,
                self._completed_phases,
                self._previous_cycle_amplitude,
                self._previous_cycle_duration,
                self._completed_cycles,
            ],
            dtype=np.float32,
        )


class RepresentationEncoder:
    """Produce one of the four pre-registered RL observation conditions."""

    def __init__(
        self,
        representation: Representation,
        *,
        raw_size: int,
        signal_index: int,
        epsilon: float = 0.0,
    ) -> None:
        if representation not in {
            "raw",
            "raw_history",
            "featuregraph",
            "augmented",
        }:
            raise ValueError(f"unknown representation: {representation}")
        if raw_size < 1:
            raise ValueError("raw_size must be positive")
        if not 0 <= signal_index < raw_size:
            raise ValueError("signal_index must identify a raw observation")
        self.representation = representation
        self.raw_size = raw_size
        self.signal_index = signal_index
        self.behavior = CausalOscillationEncoder(epsilon=epsilon)
        self._previous_raw: np.ndarray | None = None

    @property
    def output_size(self) -> int:
        feature_size = len(FEATURE_NAMES)
        return {
            "raw": self.raw_size,
            "raw_history": 2 * self.raw_size,
            "featuregraph": feature_size,
            "augmented": self.raw_size + feature_size,
        }[self.representation]

    def reset(self, observation: np.ndarray) -> np.ndarray:
        raw = self._validate_observation(observation)
        features = self.behavior.reset(float(raw[self.signal_index]))
        self._previous_raw = raw.copy()
        return self._combine(raw, features)

    def update(self, observation: np.ndarray) -> np.ndarray:
        if self._previous_raw is None:
            raise RuntimeError("reset must be called before update")
        raw = self._validate_observation(observation)
        features = self.behavior.update(float(raw[self.signal_index]))
        result = self._combine(raw, features)
        self._previous_raw = raw.copy()
        return result

    def _combine(self, raw: np.ndarray, features: np.ndarray) -> np.ndarray:
        if self.representation == "raw":
            return raw.copy()
        if self.representation == "raw_history":
            assert self._previous_raw is not None
            return np.concatenate([raw, self._previous_raw]).astype(np.float32)
        if self.representation == "featuregraph":
            return features
        return np.concatenate([raw, features]).astype(np.float32)

    def _validate_observation(self, observation: np.ndarray) -> np.ndarray:
        raw = np.asarray(observation, dtype=np.float32)
        if raw.shape != (self.raw_size,):
            raise ValueError(f"expected observation shape ({self.raw_size},)")
        if not np.isfinite(raw).all():
            raise ValueError("observation must contain only finite values")
        return raw


def _finite_scalar(value: float) -> float:
    result = float(value)
    if not np.isfinite(result):
        raise ValueError("signal must be finite")
    return result
