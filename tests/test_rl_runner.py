import numpy as np

from experiments.rl.run_dqn import ENVIRONMENTS, _normalize


def test_normalization_is_finite_and_shape_preserving() -> None:
    raw = np.array([2.4, 3.0, 0.2095, 3.5], dtype=np.float32)
    normalized = _normalize(raw, "raw", ENVIRONMENTS["cartpole"])

    np.testing.assert_allclose(normalized, np.ones(4))
    assert normalized.dtype == np.float32


def test_feature_normalization_bounds_nominal_episode_values() -> None:
    features = np.array(
        [1, 1, 200, 1.8, 1.8, 360, 1.8, 200, 200, 1.8, 200, 200],
        dtype=np.float32,
    )
    normalized = _normalize(
        features,
        "featuregraph",
        ENVIRONMENTS["mountaincar"],
    )

    np.testing.assert_allclose(normalized, np.ones(len(features)))
