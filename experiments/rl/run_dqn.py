"""Run paired DQN comparisons of raw and FeatureGraph representations."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from experiments.rl.causal_features import Representation, RepresentationEncoder

REPRESENTATIONS: tuple[Representation, ...] = (
    "raw",
    "raw_history",
    "featuregraph",
    "augmented",
)

ENVIRONMENTS = {
    "cartpole": {
        "id": "CartPole-v1",
        "signal_index": 2,
        "epsilon": 0.0,
        "default_steps": 100_000,
        "raw_scale": (2.4, 3.0, 0.2095, 3.5),
        "signal_span": 0.419,
        "episode_limit": 500,
    },
    "mountaincar": {
        "id": "MountainCar-v0",
        "signal_index": 0,
        "epsilon": 0.0,
        "default_steps": 200_000,
        "raw_scale": (1.2, 0.07),
        "signal_span": 1.8,
        "episode_limit": 200,
    },
}


@dataclass(frozen=True)
class Config:
    environment: str
    representation: Representation
    seed: int
    total_steps: int
    evaluation_interval: int = 5_000
    evaluation_episodes: int = 20
    replay_capacity: int = 100_000
    warmup_steps: int = 1_000
    batch_size: int = 128
    gamma: float = 0.99
    learning_rate: float = 1e-3
    target_update_interval: int = 1_000
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay_steps: int = 50_000


class ReplayBuffer:
    def __init__(self, capacity: int) -> None:
        self._data: deque[tuple[np.ndarray, int, float, np.ndarray, float]] = deque(
            maxlen=capacity
        )

    def __len__(self) -> int:
        return len(self._data)

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        terminal: bool,
    ) -> None:
        self._data.append((state, action, reward, next_state, float(terminal)))

    def sample(
        self, batch_size: int, rng: np.random.Generator
    ) -> tuple[np.ndarray, ...]:
        indices = rng.choice(len(self._data), size=batch_size, replace=False)
        rows = [self._data[int(index)] for index in indices]
        states, actions, rewards, next_states, terminals = zip(*rows, strict=True)
        return (
            np.stack(states),
            np.asarray(actions, dtype=np.int64),
            np.asarray(rewards, dtype=np.float32),
            np.stack(next_states),
            np.asarray(terminals, dtype=np.float32),
        )


class Adam:
    """Minimal Adam update that avoids optional Torch compiler imports."""

    def __init__(
        self,
        parameters: Any,
        torch: Any,
        *,
        learning_rate: float,
        beta1: float = 0.9,
        beta2: float = 0.999,
        epsilon: float = 1e-8,
    ) -> None:
        self.parameters = list(parameters)
        self.torch = torch
        self.learning_rate = learning_rate
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.updates = 0
        self.first_moments = [torch.zeros_like(value) for value in self.parameters]
        self.second_moments = [torch.zeros_like(value) for value in self.parameters]

    def zero_grad(self) -> None:
        for parameter in self.parameters:
            parameter.grad = None

    def step(self) -> None:
        self.updates += 1
        first_correction = 1.0 - self.beta1**self.updates
        second_correction = 1.0 - self.beta2**self.updates
        with self.torch.no_grad():
            for parameter, first, second in zip(
                self.parameters,
                self.first_moments,
                self.second_moments,
                strict=True,
            ):
                if parameter.grad is None:
                    continue
                gradient = parameter.grad
                first.mul_(self.beta1).add_(gradient, alpha=1.0 - self.beta1)
                second.mul_(self.beta2).addcmul_(
                    gradient,
                    gradient,
                    value=1.0 - self.beta2,
                )
                estimate = first / first_correction
                variance = second / second_correction
                parameter.addcdiv_(
                    estimate,
                    variance.sqrt().add_(self.epsilon),
                    value=-self.learning_rate,
                )

def run(config: Config, output_dir: Path) -> list[dict[str, float | int | str]]:
    """Train one paired-seed condition and persist its evaluation curve."""
    gym, torch, nn = _optional_dependencies()
    random.seed(config.seed)
    np.random.seed(config.seed)
    torch.manual_seed(config.seed)
    rng = np.random.default_rng(config.seed)

    spec = ENVIRONMENTS[config.environment]
    env = gym.make(spec["id"])
    evaluation_env = gym.make(spec["id"])
    initial_raw, _ = env.reset(seed=config.seed)
    raw_size = int(np.asarray(initial_raw).size)
    encoder = _encoder(config, raw_size)
    state = _normalize(encoder.reset(initial_raw), config.representation, spec)

    class QNetwork(nn.Module):
        def __init__(self, input_size: int, actions: int) -> None:
            super().__init__()
            self.layers = nn.Sequential(
                nn.Linear(input_size, 128),
                nn.ReLU(),
                nn.Linear(128, 128),
                nn.ReLU(),
                nn.Linear(128, actions),
            )

        def forward(self, values: Any) -> Any:
            return self.layers(values)

    actions = int(env.action_space.n)
    online = QNetwork(encoder.output_size, actions)
    target = QNetwork(encoder.output_size, actions)
    target.load_state_dict(online.state_dict())
    optimizer = Adam(
        online.parameters(),
        torch,
        learning_rate=config.learning_rate,
    )
    replay = ReplayBuffer(config.replay_capacity)
    curve: list[dict[str, float | int | str]] = []
    episode_index = 0

    for step in range(1, config.total_steps + 1):
        epsilon = _linear_epsilon(config, step)
        if rng.random() < epsilon:
            action = int(rng.integers(actions))
        else:
            with torch.no_grad():
                action = int(online(torch.as_tensor(state).unsqueeze(0)).argmax())

        next_raw, reward, terminated, truncated, _ = env.step(action)
        next_state = _normalize(
            encoder.update(next_raw), config.representation, spec
        )
        replay.add(state, action, reward, next_state, terminated)
        state = next_state

        if terminated or truncated:
            episode_index += 1
            initial_raw, _ = env.reset(seed=config.seed + episode_index)
            state = _normalize(
                encoder.reset(initial_raw), config.representation, spec
            )

        if len(replay) >= max(config.warmup_steps, config.batch_size):
            batch = replay.sample(config.batch_size, rng)
            _optimize(batch, online, target, optimizer, config.gamma, torch)

        if step % config.target_update_interval == 0:
            target.load_state_dict(online.state_dict())

        if step % config.evaluation_interval == 0 or step == config.total_steps:
            returns, successes = _evaluate(
                evaluation_env,
                online,
                config,
                raw_size,
                torch,
            )
            curve.append(
                {
                    "environment": config.environment,
                    "representation": config.representation,
                    "seed": config.seed,
                    "step": step,
                    "mean_return": float(np.mean(returns)),
                    "return_std": float(np.std(returns)),
                    "success_rate": float(np.mean(successes)),
                    "model_parameters": sum(
                        parameter.numel() for parameter in online.parameters()
                    ),
                }
            )

    env.close()
    evaluation_env.close()
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{config.environment}_{config.representation}_seed_{config.seed}"
    (output_dir / f"{stem}.json").write_text(
        json.dumps({"config": asdict(config), "curve": curve}, indent=2) + "\n",
        encoding="utf-8",
    )
    return curve


def _encoder(config: Config, raw_size: int) -> RepresentationEncoder:
    spec = ENVIRONMENTS[config.environment]
    return RepresentationEncoder(
        config.representation,
        raw_size=raw_size,
        signal_index=int(spec["signal_index"]),
        epsilon=float(spec["epsilon"]),
    )


def _linear_epsilon(config: Config, step: int) -> float:
    fraction = min(step / config.epsilon_decay_steps, 1.0)
    return config.epsilon_start + fraction * (
        config.epsilon_end - config.epsilon_start
    )


def _normalize(
    values: np.ndarray,
    representation: Representation,
    specification: dict[str, object],
) -> np.ndarray:
    raw_scale = np.asarray(specification["raw_scale"], dtype=np.float32)
    span = float(specification["signal_span"])
    limit = float(specification["episode_limit"])
    feature_scale = np.asarray(
        [
            1.0,
            1.0,
            limit,
            span,
            span,
            span * limit,
            span,
            limit,
            limit,
            span,
            limit,
            limit,
        ],
        dtype=np.float32,
    )
    scale = {
        "raw": raw_scale,
        "raw_history": np.concatenate([raw_scale, raw_scale]),
        "featuregraph": feature_scale,
        "augmented": np.concatenate([raw_scale, feature_scale]),
    }[representation]
    return np.clip(values / scale, -10.0, 10.0).astype(np.float32)


def _optimize(
    batch: tuple[np.ndarray, ...],
    online: Any,
    target: Any,
    optimizer: Any,
    gamma: float,
    torch: Any,
) -> None:
    states, actions, rewards, next_states, terminals = batch
    state_tensor = torch.as_tensor(states)
    action_tensor = torch.as_tensor(actions).unsqueeze(1)
    reward_tensor = torch.as_tensor(rewards)
    next_state_tensor = torch.as_tensor(next_states)
    terminal_tensor = torch.as_tensor(terminals)
    chosen_q = online(state_tensor).gather(1, action_tensor).squeeze(1)
    with torch.no_grad():
        next_q = target(next_state_tensor).max(dim=1).values
        targets = reward_tensor + gamma * (1.0 - terminal_tensor) * next_q
    loss = torch.nn.functional.smooth_l1_loss(chosen_q, targets)
    optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(online.parameters(), max_norm=10.0)
    optimizer.step()


def _evaluate(
    env: Any,
    model: Any,
    config: Config,
    raw_size: int,
    torch: Any,
) -> tuple[list[float], list[float]]:
    returns = []
    successes = []
    for episode in range(config.evaluation_episodes):
        raw, _ = env.reset(seed=1_000_000 + config.seed * 10_000 + episode)
        encoder = _encoder(config, raw_size)
        state = _normalize(
            encoder.reset(raw), config.representation, ENVIRONMENTS[config.environment]
        )
        total = 0.0
        while True:
            with torch.no_grad():
                action = int(model(torch.as_tensor(state).unsqueeze(0)).argmax())
            raw, reward, terminated, truncated, _ = env.step(action)
            state = _normalize(
                encoder.update(raw),
                config.representation,
                ENVIRONMENTS[config.environment],
            )
            total += float(reward)
            if terminated or truncated:
                success = (
                    terminated if config.environment == "mountaincar" else truncated
                )
                break
        returns.append(total)
        successes.append(float(success))
    return returns, successes


def _optional_dependencies() -> tuple[Any, Any, Any]:
    try:
        import gymnasium as gym
        import torch
        from torch import nn
    except ImportError as error:
        raise RuntimeError(
            "RL dependencies are missing; install with `pip install -e '.[rl]'`"
        ) from error
    return gym, torch, nn


def _write_combined(rows: list[dict[str, float | int | str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument(
        "--representations", nargs="+", choices=REPRESENTATIONS, default=REPRESENTATIONS
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(20)))
    parser.add_argument("--total-steps", type=int)
    parser.add_argument("--evaluation-interval", type=int, default=5_000)
    parser.add_argument("--evaluation-episodes", type=int, default=20)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/rl/results"))
    args = parser.parse_args()
    total_steps = args.total_steps or ENVIRONMENTS[args.environment]["default_steps"]
    rows = []
    for seed in args.seeds:
        for representation in args.representations:
            config = Config(
                environment=args.environment,
                representation=representation,
                seed=seed,
                total_steps=total_steps,
                evaluation_interval=args.evaluation_interval,
                evaluation_episodes=args.evaluation_episodes,
            )
            rows.extend(run(config, args.output_dir))
    _write_combined(rows, args.output_dir / f"{args.environment}_curves.csv")


if __name__ == "__main__":
    main()
