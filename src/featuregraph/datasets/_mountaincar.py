"""Reproducible MountainCar trajectories for oscillation research."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

MOUNTAINCAR_ENVIRONMENT = "MountainCar-v0"
MOUNTAINCAR_GENERATOR_VERSION = "1"
MOUNTAINCAR_SOURCE = (
    "https://gymnasium.farama.org/environments/classic_control/mountain_car/"
)

# MountainCar-v0 physical constants.
MIN_POSITION = -1.2
MAX_POSITION = 0.6
MAX_SPEED = 0.07
GOAL_POSITION = 0.5
GOAL_VELOCITY = 0.0
FORCE = 0.001
GRAVITY = 0.0025
EXPLORATION_RATE = 0.4


def mountaincar(
    *,
    episodes: int = 10,
    max_steps: int = 200,
    seed: int = 1729,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load reproducible MountainCar trajectories.

    The generated observations follow the MountainCar-v0 equations and use a
    seeded exploratory momentum policy. The policy usually builds enough
    momentum to reach the goal, while its exploration produces repeated,
    physically meaningful reversals for oscillation and accumulation research.

    Parameters
    ----------
    episodes:
        Number of independent trajectories to generate.
    max_steps:
        Maximum number of discrete simulation steps per episode.
    seed:
        Seed controlling initial positions and exploratory actions.
    refresh:
        Regenerate the cached dataset even when it already exists.

    Returns
    -------
    pandas.DataFrame
        One row per transition, with current and next physical states, action,
        reward, policy provenance, and episode-boundary flags.
    """
    _validate_parameters(episodes=episodes, max_steps=max_steps, seed=seed)

    path = _cache_path(episodes=episodes, max_steps=max_steps, seed=seed)
    if refresh or not path.exists():
        observations = _generate_trajectories(
            episodes=episodes,
            max_steps=max_steps,
            seed=seed,
        )
        temporary_path = path.with_suffix(".parquet.part")
        observations.to_parquet(temporary_path, index=False)
        temporary_path.replace(path)

    observations = pd.read_parquet(path)
    observations.attrs.update(
        {
            "mountaincar_environment": MOUNTAINCAR_ENVIRONMENT,
            "mountaincar_generator_version": MOUNTAINCAR_GENERATOR_VERSION,
            "episodes": episodes,
            "max_steps": max_steps,
            "seed": seed,
            "policy": "seeded_exploratory_momentum",
            "exploration_rate": EXPLORATION_RATE,
            "source_file": str(path),
            "source_url": MOUNTAINCAR_SOURCE,
        }
    )
    return observations


def get_mountaincar_cache_dir() -> Path:
    """Return the external cache used for generated MountainCar trajectories."""
    cache_dir = (
        Path.home()
        / ".cache"
        / "featuregraph"
        / "mountaincar"
        / MOUNTAINCAR_GENERATOR_VERSION
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def clear_mountaincar_cache() -> None:
    """Remove generated MountainCar trajectory files from the external cache."""
    cache_dir = get_mountaincar_cache_dir()
    for path in cache_dir.glob("*.parquet"):
        path.unlink()


def _cache_path(*, episodes: int, max_steps: int, seed: int) -> Path:
    filename = (
        f"mountaincar_exploratory_seed_{seed}_episodes_{episodes}_"
        f"steps_{max_steps}.parquet"
    )
    return get_mountaincar_cache_dir() / filename


def _generate_trajectories(
    *,
    episodes: int,
    max_steps: int,
    seed: int,
) -> pd.DataFrame:
    initial_rng, policy_rng = [
        np.random.default_rng(sequence)
        for sequence in np.random.SeedSequence(seed).spawn(2)
    ]
    rows: list[dict[str, object]] = []

    for episode in range(episodes):
        position = float(initial_rng.uniform(-0.6, -0.4))
        velocity = 0.0

        for step in range(max_steps):
            momentum_action = 2 if velocity >= 0 else 0
            exploratory_action = bool(policy_rng.random() < EXPLORATION_RATE)
            action = (
                int(policy_rng.integers(0, 3))
                if exploratory_action
                else momentum_action
            )
            next_position, next_velocity = _advance(position, velocity, action)
            terminated = bool(
                next_position >= GOAL_POSITION and next_velocity >= GOAL_VELOCITY
            )
            truncated = bool(step == max_steps - 1 and not terminated)

            rows.append(
                {
                    "episode": episode,
                    "step": step,
                    "time": step,
                    "episode_start": step == 0,
                    "position": position,
                    "velocity": velocity,
                    "action": action,
                    "momentum_action": momentum_action,
                    "exploratory_action": exploratory_action,
                    "reward": -1.0,
                    "next_position": next_position,
                    "next_velocity": next_velocity,
                    "terminated": terminated,
                    "truncated": truncated,
                    "episode_end": terminated or truncated,
                }
            )

            position, velocity = next_position, next_velocity
            if terminated:
                break

    return pd.DataFrame.from_records(rows)


def _advance(position: float, velocity: float, action: int) -> tuple[float, float]:
    next_velocity = velocity + (action - 1) * FORCE
    next_velocity -= np.cos(3 * position) * GRAVITY
    next_velocity = float(np.clip(next_velocity, -MAX_SPEED, MAX_SPEED))

    next_position = float(np.clip(position + next_velocity, MIN_POSITION, MAX_POSITION))
    if next_position == MIN_POSITION and next_velocity < 0:
        next_velocity = 0.0

    return next_position, next_velocity


def _validate_parameters(*, episodes: int, max_steps: int, seed: int) -> None:
    for name, value in {
        "episodes": episodes,
        "max_steps": max_steps,
        "seed": seed,
    }.items():
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{name} must be an integer")

    if episodes < 1:
        raise ValueError("episodes must be at least 1")
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")
    if seed < 0:
        raise ValueError("seed must be non-negative")
