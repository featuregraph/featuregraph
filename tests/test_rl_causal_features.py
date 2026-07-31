import numpy as np
import pytest

from experiments.rl.causal_features import (
    FEATURE_NAMES,
    CausalOscillationEncoder,
    RepresentationEncoder,
)


def test_causal_encoder_detects_phases_and_complete_cycle() -> None:
    encoder = CausalOscillationEncoder()
    rows = [encoder.reset(0.0)]
    rows.extend(encoder.update(value) for value in [1.0, 2.0, 1.0, 0.0, 1.0])
    features = np.stack(rows)
    index = {name: FEATURE_NAMES.index(name) for name in FEATURE_NAMES}

    assert features[:, index["reversal"]].tolist() == [0, 0, 0, 1, 0, 1]
    assert features[-1, index["completed_phases"]] == 2
    assert features[-1, index["completed_cycles"]] == 0

    final = encoder.update(2.0)
    after_peak = encoder.update(1.0)
    assert final[index["completed_cycles"]] == 0
    assert after_peak[index["completed_cycles"]] == 1
    assert after_peak[index["previous_cycle_duration"]] == 4
    assert after_peak[index["previous_cycle_amplitude"]] == 2


def test_features_are_prefix_causal() -> None:
    shared_prefix = [0.0, 1.0, 2.0, 1.0]

    def encode(values: list[float]) -> np.ndarray:
        encoder = CausalOscillationEncoder()
        rows = [encoder.reset(values[0])]
        rows.extend(encoder.update(value) for value in values[1:])
        return np.stack(rows)

    first = encode(shared_prefix + [0.0, -1.0])
    second = encode(shared_prefix + [3.0, 4.0])
    np.testing.assert_array_equal(
        first[: len(shared_prefix)], second[: len(shared_prefix)]
    )


def test_reset_prevents_cross_episode_state_leakage() -> None:
    encoder = CausalOscillationEncoder()
    encoder.reset(0.0)
    encoder.update(1.0)
    encoder.update(0.0)

    reset_features = encoder.reset(10.0)
    fresh_features = CausalOscillationEncoder().reset(10.0)
    np.testing.assert_array_equal(reset_features, fresh_features)


@pytest.mark.parametrize(
    ("representation", "size"),
    [
        ("raw", 4),
        ("raw_history", 8),
        ("featuregraph", len(FEATURE_NAMES)),
        ("augmented", 4 + len(FEATURE_NAMES)),
    ],
)
def test_representation_shapes(representation: str, size: int) -> None:
    encoder = RepresentationEncoder(
        representation,  # type: ignore[arg-type]
        raw_size=4,
        signal_index=2,
    )
    initial = encoder.reset(np.array([0.0, 0.0, 0.1, 0.0]))
    updated = encoder.update(np.array([0.0, 0.0, 0.2, 0.0]))

    assert initial.shape == (size,)
    assert updated.shape == (size,)
    assert encoder.output_size == size


def test_raw_history_uses_only_current_and_previous_observation() -> None:
    encoder = RepresentationEncoder("raw_history", raw_size=2, signal_index=0)
    first = np.array([1.0, 2.0])
    second = np.array([3.0, 4.0])

    np.testing.assert_array_equal(encoder.reset(first), [1.0, 2.0, 1.0, 2.0])
    np.testing.assert_array_equal(encoder.update(second), [3.0, 4.0, 1.0, 2.0])


def test_encoder_rejects_invalid_state() -> None:
    with pytest.raises(ValueError):
        CausalOscillationEncoder(epsilon=-1)
    with pytest.raises(ValueError):
        RepresentationEncoder("unknown", raw_size=2, signal_index=0)  # type: ignore[arg-type]

    encoder = RepresentationEncoder("raw", raw_size=2, signal_index=0)
    with pytest.raises(RuntimeError):
        encoder.update(np.array([0.0, 1.0]))
    with pytest.raises(ValueError):
        encoder.reset(np.array([0.0]))
