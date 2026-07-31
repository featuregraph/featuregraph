from pathlib import Path

import pandas as pd
import pytest

import featuregraph as fg
from featuregraph.datasets._mountaincar import (
    EXPLORATION_RATE,
    MOUNTAINCAR_ENVIRONMENT,
    MOUNTAINCAR_GENERATOR_VERSION,
    _generate_trajectories,
    mountaincar,
)

EXPECTED_COLUMNS = [
    "episode",
    "step",
    "time",
    "episode_start",
    "position",
    "velocity",
    "action",
    "momentum_action",
    "exploratory_action",
    "reward",
    "next_position",
    "next_velocity",
    "terminated",
    "truncated",
    "episode_end",
]


def test_generate_trajectories_is_deterministic() -> None:
    first = _generate_trajectories(episodes=3, max_steps=200, seed=1729)
    second = _generate_trajectories(episodes=3, max_steps=200, seed=1729)

    pd.testing.assert_frame_equal(first, second)


def test_generated_dataset_has_expected_schema_and_boundaries() -> None:
    observations = _generate_trajectories(episodes=4, max_steps=200, seed=1729)

    assert observations.columns.tolist() == EXPECTED_COLUMNS
    assert observations["episode"].nunique() == 4
    assert observations.groupby("episode")["step"].min().eq(0).all()
    assert observations.groupby("episode")["episode_start"].sum().eq(1).all()
    assert observations["action"].isin([0, 1, 2]).all()
    assert observations["momentum_action"].isin([0, 2]).all()
    assert observations["reward"].eq(-1.0).all()
    assert observations["position"].between(-1.2, 0.6).all()
    assert observations["velocity"].between(-0.07, 0.07).all()

    final_rows = observations.groupby("episode", sort=False).tail(1)
    assert (final_rows["terminated"] | final_rows["truncated"]).all()
    assert final_rows["episode_end"].all()

    next_rows = observations.groupby("episode", sort=False).shift(-1)
    interior = ~observations["episode_end"]
    assert observations.loc[interior, "next_position"].equals(
        next_rows.loc[interior, "position"]
    )
    assert observations.loc[interior, "next_velocity"].equals(
        next_rows.loc[interior, "velocity"]
    )


def test_exploratory_trajectory_contains_repeated_position_reversals() -> None:
    observations = _generate_trajectories(episodes=10, max_steps=200, seed=1729)
    reversals = observations.groupby("episode")["velocity"].apply(
        lambda values: (values.mul(values.shift()) < 0).sum()
    )

    assert reversals.ge(2).all()
    assert observations.groupby("episode")["exploratory_action"].any().all()


def test_mountaincar_supports_oscillation_and_accumulation_workflow() -> None:
    observations = _generate_trajectories(episodes=4, max_steps=200, seed=1729)

    oscillation = fg.oscillation.Oscillation(
        signals="position",
        group="episode",
        smooth_signal=False,
    )
    oscillation_features = oscillation.fit_transform(observations)
    oscillation_objects = oscillation.summarize(
        oscillation_features,
        signal="position",
    )

    accumulation = fg.accumulation.Accumulation(
        signals="position",
        group="episode",
    )
    accumulation_features = accumulation.fit_transform(oscillation_features)
    accumulation_objects = accumulation.summarize(
        accumulation_features,
        signal="position",
    )

    assert oscillation_objects.count > 0
    assert accumulation_objects.count == oscillation_objects.count


def test_mountaincar_uses_cache_and_restores_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "featuregraph.datasets._mountaincar.get_mountaincar_cache_dir",
        lambda: tmp_path,
    )

    generated = mountaincar(episodes=2, max_steps=50, seed=11)
    cached = mountaincar(episodes=2, max_steps=50, seed=11)

    pd.testing.assert_frame_equal(generated, cached)
    assert cached.attrs["mountaincar_environment"] == MOUNTAINCAR_ENVIRONMENT
    assert (
        cached.attrs["mountaincar_generator_version"]
        == MOUNTAINCAR_GENERATOR_VERSION
    )
    assert cached.attrs["episodes"] == 2
    assert cached.attrs["max_steps"] == 50
    assert cached.attrs["seed"] == 11
    assert cached.attrs["policy"] == "seeded_exploratory_momentum"
    assert cached.attrs["exploration_rate"] == EXPLORATION_RATE
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
def test_mountaincar_rejects_invalid_parameters(
    kwargs: dict[str, object],
    exception: type[Exception],
) -> None:
    with pytest.raises(exception):
        mountaincar(**kwargs)  # type: ignore[arg-type]
