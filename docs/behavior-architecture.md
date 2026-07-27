# Behavior architecture

FeatureGraph converts ordered observations into explicit, temporally bounded behavioral objects. The current implementation uses three compositional layers:

`ordered observations → Transition → Oscillation → Accumulation`

Each layer has two representations:

- a feature frame with one row per source observation and additional state, boundary, measurement, and object-identity columns;
- an object table with one row per `(group, signal, object_id)` and intrinsic properties plus provenance.

## Transition

`Transition` is the first-order behavioral layer. For every signal, each observation is classified as:

- rising, when the lagged change exceeds `eps`;
- falling, when the lagged change is less than `-eps`;
- inactive, when the change remains within the sensitivity band.

Contiguous observations in the same state form a transition object. Each object has a stable identifier, start and end boundaries, a completeness flag, point count, sample duration, optional elapsed-time duration, start and end values, net change, and mean and peak rate.

The two sensitivity parameters have distinct roles:

- `diff_lag` is the observation-space comparison interval;
- `eps` is the value-space minimum directional change.

They are stored with the objects as provenance. An optional `time` coordinate
controls physical durations and rates; numeric time uses its native units and
datetime time is normalized to seconds. Group boundaries are respected, so
state and identity never leak between independent records.

## Oscillation

`Oscillation` composes the transition layer. Rising and falling behavior is not independently redefined inside the oscillation construction; it comes from `Transition` using the same signal, grouping, lag, and sensitivity parameters.

Peaks and troughs delimit waves. Each complete oscillation is a bounded wave with stable identity and intrinsic measurements such as sample duration, optional elapsed-time duration, period, and amplitude. Partial edge waves remain identifiable and carry an explicit completeness state rather than being silently discarded.

This composition preserves the observation-level transition columns needed for inspection while producing an oscillation object table for relational work.

## Accumulation

`Accumulation` is derived from oscillation waves. It preserves an explicit
`parent_oscillation_id` and the parent completeness semantics while measuring
wave-level accumulation behavior. Without `time`, accumulation retains the
sample-sum contract. With `time`, it uses trapezoidal integration over the
supplied coordinate, including irregular intervals.

Because the outward Oscillation contract remains stable, adding the explicit Transition layer does not require a separate accumulation interpretation. Accumulation continues to operate on the same wave boundaries and parent identifiers.

## Invariants

The current implementation and tests enforce these structural expectations:

- source row count and source ordering are preserved in feature frames;
- independent groups are processed independently;
- object identifiers are deterministic and contiguous within their scope;
- transitions partition directional behavior into rising, falling, and inactive states;
- higher-order objects retain inspectable links to their parents;
- partial boundary objects are represented explicitly;
- flat regions, missing values, multiple signals, grouped records, string
  indexes, and irregular time do not create cross-boundary objects;
- indexes are unique and optional time coordinates are nonmissing and strictly
  increasing within each group;
- object tables contain provenance sufficient to identify the construction parameters.

## Validation

The repository validates the hierarchy at three levels:

- unit and integration tests cover transitions, oscillations, accumulations, queries, grouping, boundaries, missing values, smoothing, and multiple signals;
- all tutorial notebooks are parsed, compiled, and executed against the current API;
- the pinned BIDMC and Tennessee Eastman reproduction pipeline writes transition, oscillation, and accumulation object tables and verifies their structural assertions.

The normative definitions are in `docs/behavior-semantics.md`. Held-out
synthetic evaluation is included with the beta candidate; broader expert
boundary validation on real data remains active research work.
