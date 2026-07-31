# Behavior architecture

> **Development documentation:** This page describes the unreleased architecture on `main`. It is not the API released as FeatureGraph `v0.1.0a1`. For the working alpha implementation, use [`alpha/v0.1.x`](https://github.com/featuregraph/featuregraph/tree/alpha/v0.1.x); for exact research reproduction, use [`v0.1.0a1`](https://github.com/featuregraph/featuregraph/tree/v0.1.0a1).

FeatureGraph converts ordered observations into explicit, temporally bounded behavioral objects. The development architecture is exploring this composition:

`ordered observations → Transition summaries → Oscillation → Accumulation`

The replacement contracts remain subject to change. Migration guidance will be published only after the interface stabilizes.

## Transition

`Transition` is the only first-order layer that interprets the observation sequence. It constructs sample-level states and events and produces one row per contiguous transition. Candidate summary properties include identity, state, boundaries, duration, representative level, variability, net change, and rates.

The principal sensitivity controls are:

- `diff_lag`: the observation-space comparison interval;
- `eps`: the value-space minimum directional change.

Group boundaries must be respected so state and identity do not leak between independent records.

## Oscillation

The development `Oscillation` object is derived from transition outputs rather than reinterpreting the raw signal independently. It composes compatible rising and falling transitions into bounded waves with explicit extrema, identity, duration, amplitude, symmetry, and completeness.

## Accumulation

The development direction is to derive accumulation from explicit intervals and contribution definitions supplied by earlier representations. The released alpha instead implements wave-derived accumulation inside parent oscillation boundaries. These contracts should not be treated as interchangeable.

## Invariants under development

The implementation and tests are expected to enforce that:

- feature frames preserve source row count and ordering;
- independent groups are isolated;
- identifiers are deterministic within scope;
- incomplete boundary objects remain explicit;
- higher-order objects preserve inspectable links to their inputs;
- object tables retain construction provenance.

Formal semantics, stable class boundaries, and migration from the alpha API remain active work.
