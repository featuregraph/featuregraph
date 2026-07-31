from pathlib import Path

import pandas as pd
import pytest

import featuregraph as fg
from featuregraph.datasets._cartpole import (
    CARTPOLE_ENVIRONMENT,
    CARTPOLE_GENERATOR_VERSION,
    _generate_trajectories,
    cartpole,
)

EXPECTED_COLUMNS = [
    "episode",
    "step",
    "time",
    "episode_start",
    "cart_position",
    "cart_velocity",
    "pole_angle",
    "pole_angular_velocity",
    "action",
    "control_score",
    "reward",
    "next_cart_position",
    "next_cart_velocity",
    "next_pole_angle",
    "next_pole_angular_velocity",
    "terminated",
    "truncated",
    "episode_end",
]


def test_generate_trajectories_is_deterministic() -> None:
    first = _generate_trajectories(episodes=3, max_steps=100, seed=1729)
    second = _generate_trajectories(episodes=3, max_steps=100, seed=1729)

    pd.testing.assert_frame_equal(first, second)


def test_generated_dataset_has_expected_schema_and_boundaries() -> None:
    observations = _generate_trajectories(
        episodes=4,
        max_steps=200,
        seed=1729,
    )

    assert observations.columns.tolist() == EXPECTED_COLUMNS
    assert observations["episode"].nunique() == 4
    assert observations.groupby("episode")["step"].min().eq(0).all()
    assert observations.groupby("episode")["episode_start"].sum().eq(1).all()
    assert observations["action"].isin([0, 1]).all()
    assert observations["reward"].eq(1.0).all()

    final_rows = observations.groupby("episode", sort=False).tail(1)
    assert (final_rows["terminated"] | final_rows["truncated"]).all()
    assert final_rows["episode_end"].all()

    next_rows = observations.groupby("episode", sort=False).shift(-1)
    interior = ~observations["episode_end"]
    assert observations.loc[interior, "next_pole_angle"].equals(
        next_rows.loc[interior, "pole_angle"]
    )


def test_feedback_trajectory_contains_repeated_pole_reversals() -> None:
    observations = _generate_trajectories(
        episodes=5,
        max_steps=500,
        seed=1729,
    )

    reversals = observations.groupby("episode")["pole_angular_velocity"].apply(
        lambda values: (values.mul(values.shift()) < 0).sum()
    )

    assert reversals.ge(10).all()


def test_cartpole_supports_oscillation_and_accumulation_workflow() -> None:
    observations = _generate_trajectories(
        episodes=2,
        max_steps=200,
        seed=1729,
    )

    oscillation = fg.oscillation.Oscillation(
        signals="pole_angle",
        group="episode",
        smooth_signal=False,
    )
    oscillation_features = oscillation.fit_transform(observations)
    oscillation_objects = oscillation.summarize(
        oscillation_features,
        signal="pole_angle",
    )

    accumulation = fg.accumulation.Accumulation(
        signals="pole_angle",
        group="episode",
    )
    accumulation_features = accumulation.fit_transform(oscillation_features)
    accumulation_objects = accumulation.summarize(
        accumulation_features,
        signal="pole_angle",
    )

    assert oscillation_objects.count > 0
    assert accumulation_objects.count == oscillation_objects.count


def test_cartpole_uses_cache_and_restores_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "featuregraph.datasets._cartpole.get_cartpole_cache_dir",
        lambda: tmp_path,
    )

    generated = cartpole(episodes=2, max_steps=50, seed=11)
    cached = cartpole(episodes=2, max_steps=50, seed=11)

    pd.testing.assert_frame_equal(generated, cached)
    assert cached.attrs["cartpole_environment"] == CARTPOLE_ENVIRONMENT
    assert cached.attrs["cartpole_generator_version"] == CARTPOLE_GENERATOR_VERSION
    assert cached.attrs["episodes"] == 2
    assert cached.attrs["max_steps"] == 50
    assert cached.attrs["seed"] == 11
    assert cached.attrs["policy"] == "deterministic_feedback"
    assert cached.attrs["control_interval"] == 4
    assert Path(cached.attrs["source_file"]).is_file()


@pytest.mark.parametrize(
    ("kwargs", "exception"),
    [
        ({"episodes": 0}, ValueError),
        ({"max_steps": 0}, ValueError),
        ({"seed": -1}, ValueError),
        ({"episodes": 1.5}, TypeError),
        ({"max_steps": True}, TypeError),
    ],
)
def test_cartpole_rejects_invalid_parameters(
    kwargs: dict[str, object],
    exception: type[Exception],
) -> None:
    with pytest.raises(exception):
        cartpole(**kwargs)  # type: ignore[arg-type]
