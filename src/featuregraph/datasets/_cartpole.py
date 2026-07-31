"""Deterministic CartPole trajectories for oscillation research."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

CARTPOLE_ENVIRONMENT = "CartPole-v1"
CARTPOLE_GENERATOR_VERSION = "1"
CARTPOLE_SOURCE = "https://gymnasium.farama.org/environments/classic_control/cart_pole/"

# CartPole-v1 physical constants.
GRAVITY = 9.8
MASS_CART = 1.0
MASS_POLE = 0.1
TOTAL_MASS = MASS_CART + MASS_POLE
HALF_POLE_LENGTH = 0.5
POLE_MASS_LENGTH = MASS_POLE * HALF_POLE_LENGTH
FORCE_MAGNITUDE = 10.0
TIME_STEP = 0.02
CONTROL_INTERVAL = 4
CART_POSITION_THRESHOLD = 2.4
POLE_ANGLE_THRESHOLD = 12 * 2 * np.pi / 360


def cartpole(
    *,
    episodes: int = 10,
    max_steps: int = 500,
    seed: int = 1729,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load deterministic feedback-controlled CartPole trajectories.

    The generated observations follow the CartPole-v1 equations and use a
    fixed, inspectable feedback policy. The policy is intended to keep the
    pole near upright while producing repeated corrective oscillations in
    pole angle, angular velocity, cart position, and cart velocity.

    Parameters
    ----------
    episodes:
        Number of independent trajectories to generate.
    max_steps:
        Maximum number of 20 ms simulation steps per episode.
    seed:
        Seed controlling the initial state of each episode.
    refresh:
        Regenerate the cached dataset even when it already exists.

    Returns
    -------
    pandas.DataFrame
        One row per simulation step, with episode and step identifiers,
        physical state variables, the applied action, reward, and boundary
        flags.
    """
    _validate_parameters(
        episodes=episodes,
        max_steps=max_steps,
        seed=seed,
    )

    path = _cache_path(
        episodes=episodes,
        max_steps=max_steps,
        seed=seed,
    )

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
            "cartpole_environment": CARTPOLE_ENVIRONMENT,
            "cartpole_generator_version": CARTPOLE_GENERATOR_VERSION,
            "episodes": episodes,
            "max_steps": max_steps,
            "seed": seed,
            "policy": "deterministic_feedback",
            "time_step": TIME_STEP,
            "control_interval": CONTROL_INTERVAL,
            "source_file": str(path),
            "source_url": CARTPOLE_SOURCE,
        }
    )
    return observations


def get_cartpole_cache_dir() -> Path:
    """Return the external cache used for generated CartPole trajectories."""
    cache_dir = (
        Path.home()
        / ".cache"
        / "featuregraph"
        / "cartpole"
        / CARTPOLE_GENERATOR_VERSION
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def clear_cartpole_cache() -> None:
    """Remove generated CartPole trajectory files from the external cache."""
    cache_dir = get_cartpole_cache_dir()
    for path in cache_dir.glob("*.parquet"):
        path.unlink()


def _cache_path(*, episodes: int, max_steps: int, seed: int) -> Path:
    filename = (
        f"cartpole_feedback_seed_{seed}_episodes_{episodes}_steps_{max_steps}.parquet"
    )
    return get_cartpole_cache_dir() / filename


def _generate_trajectories(
    *,
    episodes: int,
    max_steps: int,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []

    for episode in range(episodes):
        state = rng.uniform(low=-0.05, high=0.05, size=4)
        action = 0

        for step in range(max_steps):
            cart_position, cart_velocity, pole_angle, pole_angular_velocity = state
            control_score = _feedback_score(state)
            if step % CONTROL_INTERVAL == 0:
                action = int(control_score > 0)
            next_state = _advance(state, action)
            (
                next_cart_position,
                next_cart_velocity,
                next_pole_angle,
                next_pole_angular_velocity,
            ) = next_state

            terminated = bool(
                abs(next_cart_position) > CART_POSITION_THRESHOLD
                or abs(next_pole_angle) > POLE_ANGLE_THRESHOLD
            )
            truncated = bool(step == max_steps - 1 and not terminated)

            rows.append(
                {
                    "episode": episode,
                    "step": step,
                    "time": step * TIME_STEP,
                    "episode_start": step == 0,
                    "cart_position": cart_position,
                    "cart_velocity": cart_velocity,
                    "pole_angle": pole_angle,
                    "pole_angular_velocity": pole_angular_velocity,
                    "action": action,
                    "control_score": control_score,
                    "reward": 1.0,
                    "next_cart_position": next_cart_position,
                    "next_cart_velocity": next_cart_velocity,
                    "next_pole_angle": next_pole_angle,
                    "next_pole_angular_velocity": next_pole_angular_velocity,
                    "terminated": terminated,
                    "truncated": truncated,
                    "episode_end": terminated or truncated,
                }
            )

            state = next_state
            if terminated:
                break

    return pd.DataFrame.from_records(rows)


def _feedback_score(state: np.ndarray) -> float:
    cart_position, cart_velocity, pole_angle, pole_angular_velocity = state
    return float(
        pole_angle
        + 0.25 * pole_angular_velocity
        + 0.01 * cart_position
        + 0.05 * cart_velocity
    )


def _advance(state: np.ndarray, action: int) -> np.ndarray:
    cart_position, cart_velocity, pole_angle, pole_angular_velocity = state
    force = FORCE_MAGNITUDE if action == 1 else -FORCE_MAGNITUDE
    cosine = np.cos(pole_angle)
    sine = np.sin(pole_angle)

    temporary = (
        force + POLE_MASS_LENGTH * pole_angular_velocity**2 * sine
    ) / TOTAL_MASS
    pole_angular_acceleration = (GRAVITY * sine - cosine * temporary) / (
        HALF_POLE_LENGTH * (4.0 / 3.0 - MASS_POLE * cosine**2 / TOTAL_MASS)
    )
    cart_acceleration = (
        temporary - POLE_MASS_LENGTH * pole_angular_acceleration * cosine / TOTAL_MASS
    )

    return np.array(
        [
            cart_position + TIME_STEP * cart_velocity,
            cart_velocity + TIME_STEP * cart_acceleration,
            pole_angle + TIME_STEP * pole_angular_velocity,
            pole_angular_velocity + TIME_STEP * pole_angular_acceleration,
        ],
        dtype=float,
    )


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
