# Behavioral objects

A time series contains ordered values. Behaviors such as transitions,
oscillations, and accumulations remain implicit until their states, boundaries,
identities, and properties are constructed.

FeatureGraph separates this construction into layers:

```text
ordered observations
    → sample-level states and events
    → object identities and boundaries
    → one-row-per-object tables
    → computational queries
```

## Observations

Observations are the original ordered samples and their grouping context.
FeatureGraph preserves their order and keeps independent sequences isolated.

## States and events

A state is a sample-aligned condition, such as rising, falling, or inactive.
Events identify changes in those conditions, such as entering or exiting a
state.

## Object identity

Events define temporal boundaries. FeatureGraph assigns deterministic identities
between compatible boundaries so each bounded behavior can be inspected as one
object.

## Object properties

Each object table records intrinsic properties such as duration, extrema,
change, rate, amplitude, symmetry, or accumulated contribution when those
properties are defined for that behavior.

## Queries

The object table becomes the interface for downstream computation. Consumers can
filter, compare, aggregate, and relate objects without reconstructing the
behavior from the raw samples each time.
