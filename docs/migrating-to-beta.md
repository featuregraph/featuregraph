# Migrating from 0.1 alpha to 0.2 beta

FeatureGraph 0.2 beta completes the initial Transition → Oscillation →
Accumulation hierarchy. Existing alpha Oscillation and Accumulation calls
without a time column remain valid.

## New behavior and relations

- `Transition` is public and supplies the directional layer used by
  Oscillation.
- Accumulation tables now include `parent_oscillation_id`.
- Transition and Oscillation tables include explicit sample-duration fields.
- Accumulation tables distinguish observation count and edge duration.

## Optional time-aware construction

Pass `time="column_name"` to all behaviors in a composed pipeline. Time must
be numeric or datetime-like and strictly increasing within each group.

When time is supplied:

- Transition rates divide by actual elapsed time.
- Oscillation duration and period use actual elapsed time.
- Accumulation uses trapezoidal integration.

Without time, beta preserves the alpha sample-space conventions.

## Validation changes

Beta rejects duplicate source indexes, missing time values, and time that is
not strictly increasing within a group. FeatureGraph continues to preserve
input order rather than sorting silently.

## Version and archive distinction

`v0.1.0a1` remains the archived implementation for alpha results. Results
produced with `0.2.0b1` should cite the eventual beta archive rather than the
alpha version DOI. Until that archive exists, use the FeatureGraph concept DOI
and identify the exact source commit.
