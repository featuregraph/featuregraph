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

## Shape measures

`featuregraph.shape` holds measures that read the observations
`compile_states` returns and nothing else. They know how long a run lasts and
where in the record it sits. They do not know what the column was, and they
do not need to. That is the line between structural and analytical
understanding on one side and scientific understanding on the other.

- `occurrences` gives one row per occurrence: state, start and end position
  within the group, and sample count. Positions count rows of the record, so
  an occurrence compiled under `missing_policy: "exclude"` still sits where it
  sat.
- `rise_fall_asymmetry` gives one row per rising occurrence with the rising
  share of the rise-and-fall pair that follows it. 0.5 is symmetric; above
  0.5 is a slow rise and a fast fall. A rise not followed by a fall is
  reported with `paired` set to `False`, not dropped.
- `occurrence_drift` fits, for each group and state, a line of a
  per-occurrence measure against where the occurrence starts, with position
  normalised over the record. The slope is the fitted change from the start
  of the record to its end, alongside first-half and second-half medians for
  a reading that does not depend on the fit.

Whether an asymmetry of 0.7 or a drift of three samples per record means
anything is a scientific question, and stays outside these functions.
