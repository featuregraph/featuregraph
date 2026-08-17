# Datasets

FeatureGraph provides narrow loaders for the fixed datasets used by the alpha
research line. Loaders return ordinary pandas data frames and attach provenance
and construction metadata through `DataFrame.attrs`.

## CartPole oscillation dataset

`featuregraph.datasets.cartpole()` generates deterministic CartPole-v1
trajectories from the published physical equations. A seeded, inspectable
feedback controller holds each action for four 20 ms simulation steps. This
produces bounded corrective motion with repeated reversals rather than random,
rapidly terminated episodes.

```python
import featuregraph as fg

cartpole = fg.datasets.cartpole(
    episodes=10,
    max_steps=500,
    seed=1729,
)
```

Each row is an RL-compatible transition containing the current state, action,
reward, next state, and episode-boundary flags. The current-state columns also
form the ordered observation sequence used by FeatureGraph.

The returned columns are:

| Column | Meaning |
| --- | --- |
| `episode` | Independent trajectory identifier |
| `step` | Zero-based simulation step within the episode |
| `time` | Elapsed time in seconds |
| `episode_start` | First transition in an episode |
| `cart_position` | Horizontal cart position |
| `cart_velocity` | Horizontal cart velocity |
| `pole_angle` | Pole angle in radians from upright |
| `pole_angular_velocity` | Pole angular velocity |
| `action` | Applied force direction, 0 or 1 |
| `control_score` | Deterministic feedback score before the action |
| `reward` | CartPole reward for the step |
| `next_cart_position` | Cart position after the action |
| `next_cart_velocity` | Cart velocity after the action |
| `next_pole_angle` | Pole angle after the action |
| `next_pole_angular_velocity` | Pole angular velocity after the action |
| `terminated` | Physical failure boundary reached |
| `truncated` | Configured maximum episode length reached |
| `episode_end` | Either termination or truncation occurred |

The default dataset is cached outside the repository. Use `refresh=True` to
regenerate it from the same seed and equations.

```{note}
The CartPole loader is included in `v0.1.0b1`. Install the maintained branch
to use subsequent compatible research-line changes before another release.
```

### Construct behavioral objects

Treat `pole_angle` as the signal and `episode` as the independent group:

```python
cartpole_oscillation = fg.oscillation.Oscillation(
    signals="pole_angle",
    group="episode",
    smooth_signal=False,
)
cartpole_oscillation_features = cartpole_oscillation.fit_transform(cartpole)
cartpole_oscillation_objects = cartpole_oscillation.summarize(
    cartpole_oscillation_features,
    signal="pole_angle",
)

cartpole_accumulation = fg.accumulation.Accumulation(
    signals="pole_angle",
    group="episode",
)
cartpole_accumulation_features = cartpole_accumulation.fit_transform(
    cartpole_oscillation_features
)
cartpole_accumulation_objects = cartpole_accumulation.summarize(
    cartpole_accumulation_features,
    signal="pole_angle",
)
```

This representation lets us compare pole-angle cycles across episodes while
retaining the controller actions and the cart variables needed to study their
physical and behavioral relationships.

## MountainCar oscillation dataset

`featuregraph.datasets.mountaincar()` reproduces the MountainCar-v0 equations
without adding a Gymnasium dependency. Its seeded exploratory momentum policy
creates repeated valley traversals, while preserving successful and truncated
episodes for later reinforcement-learning comparisons.

```python
mountaincar = fg.datasets.mountaincar(
    episodes=10,
    max_steps=200,
    seed=1729,
)
```

Each row is an RL-compatible transition. Current state is stored in `position`
and `velocity`; `next_position` and `next_velocity` contain the resulting state.
Actions are `0` (left), `1` (neutral), or `2` (right). The
`momentum_action` and `exploratory_action` columns make the behavior policy
auditable. MountainCar gives `-1.0` reward per step until the goal or time limit.

Construct position-based behavioral objects independently within each episode:

```python
mountaincar_oscillation = fg.oscillation.Oscillation(
    signals="position",
    group="episode",
    smooth_signal=False,
)
mountaincar_oscillation_features = mountaincar_oscillation.fit_transform(
    mountaincar
)
mountaincar_oscillation_objects = mountaincar_oscillation.summarize(
    mountaincar_oscillation_features,
    signal="position",
)

mountaincar_accumulation = fg.accumulation.Accumulation(
    signals="position",
    group="episode",
)
mountaincar_accumulation_features = mountaincar_accumulation.fit_transform(
    mountaincar_oscillation_features
)
mountaincar_accumulation_objects = mountaincar_accumulation.summarize(
    mountaincar_accumulation_features,
    signal="position",
)
```

The cached data records the environment, generator version, policy,
exploration rate, seed, construction parameters, source URL, and cache path in
`DataFrame.attrs`.
