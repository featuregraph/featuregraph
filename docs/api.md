# Beta API reference

## Shared contract

All behaviors accept:

- `signals`: one signal name or a sequence of names;
- `group`: no grouping, one group column, or several group columns;
- `time`: an optional numeric or datetime column that is strictly increasing
  within each group.

`fit_transform(frame)` returns a copy of the observation frame with
construction evidence. `summarize(features, signal, include_partial=False)`
returns `BehaviorObjects`.

`BehaviorObjects` exposes:

- `table`: one row per object;
- `features`: the supporting observation-level representation;
- `properties`: the stable object property names;
- `construction`: constructor parameters and semantic choices;
- `query()`: deterministic filtering, selection, ordering, and limiting.

## Transition

```python
transition = fg.transition.Transition(
    signals="signal",
    group="record",
    time="seconds",
    diff_lag=2,
    eps=0.001,
)
features = transition.fit_transform(observations)
objects = transition.summarize(features, "signal")
```

The stable object schema includes identity, direction, completeness, source
and time boundaries, duration in samples and time units, values, change, and
rates.

## Oscillation

```python
oscillation = fg.oscillation.Oscillation(
    signals="signal",
    group="record",
    time="seconds",
    diff_lag=2,
    eps=0.001,
    smooth_signal=False,
)
features = oscillation.fit_transform(observations)
objects = oscillation.summarize(features, "signal")
```

Oscillation composes Transition internally. Its schema includes source and
time boundaries, sample and time durations, amplitude, phase rates, period,
symmetry, and completeness.

## Accumulation

```python
accumulation = fg.accumulation.Accumulation(
    signals="signal",
    group="record",
    time="seconds",
    threshold="min",
)
features = accumulation.fit_transform(oscillation_features)
objects = accumulation.summarize(features, "signal")
```

The schema includes `parent_oscillation_id`, boundaries, durations, baseline,
signed total area, phase areas, mean and peak rate, centroid, symmetry, and
half-accumulation time. `construction["integration"]` is `sample_sum` without
time and `trapezoidal` with time.

## Query

```python
result = (
    objects.query()
    .where(duration__ge=10, is_complete=True)
    .select("oscillation_id", "duration", "amplitude")
    .order_by("amplitude", ascending=False)
    .limit(10)
    .collect()
)
```

Supported operators are equality, inequality, comparisons, and membership:
`eq`, `ne`, `gt`, `ge`, `lt`, `le`, and `in`.
