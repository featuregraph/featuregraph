# Authoritative behavior semantics

This specification is the authority for FeatureGraph 0.2 beta behavior
construction. Code, tests, notebooks, object schemas, and research prose
should use these definitions.

## Shared observation contract

Input is a pandas `DataFrame` whose current row order is the declared
observation order. FeatureGraph does not silently sort observations.

- Every configured signal and group column must exist.
- The source index must be unique because object boundaries retain its labels.
- Stateful operations are isolated within every configured group.
- If `time` is supplied, it must be numeric or datetime-like, nonmissing, and
  strictly increasing within each group.
- `diff_lag` is always measured in observations, even when physical time is
  available.
- A feature frame preserves the input rows and index.
- An object table contains one row per `(group, signal, object_id)`.

For datetime input, internal elapsed-time calculations use seconds. Numeric
time retains its declared unit. When no time column is supplied, durations and
rates are expressed in observation-space units.

## Transition

For signal \(x_i\), lag \(L \ge 1\), and sensitivity
\(\epsilon \ge 0\), define

\[
\Delta_i = x_i - x_{i-L}.
\]

Each observation with a finite difference is assigned exactly one direction:

- rising when \(\Delta_i > \epsilon\);
- falling when \(\Delta_i < -\epsilon\);
- inactive when \(|\Delta_i| \le \epsilon\).

Rows without a finite lagged difference have no directional state. A maximal
contiguous run of one direction is a transition object. Missing signal values
break continuity because the associated differences have no direction.

An entry occurs when a directional mask changes from false to true. The
transition starts at the preceding observation and ends at the final
observation before the next directional entry. A transition ending at the
right boundary of a group is partial; it is retained only when
`include_partial=True`.

Intrinsic properties are direction, completeness, source-index boundaries,
time boundaries, duration in samples and configured time units, start and end
values, signed net change, signed mean rate, and peak absolute local rate.

## Oscillation

Oscillation uses the exact Transition states produced from the same signals,
groups, lag, epsilon, time column, and optional smoothed working signal.

- Exiting rising marks a peak at the preceding observation.
- Entering rising marks a trough at the preceding observation.
- A complete oscillation is a strictly ordered trough–peak–trough interval.
- The first and last boundary-truncated waves remain identifiable as partial.
- Flat regions are inactive transitions and remain within the surrounding
  extrema-defined interval.

Amplitude is half the difference between the maximum and minimum working
signal in the wave. Rise, fall, and total duration are boundary differences.
Period is the distance between consecutive peaks within the same group.
Temporal symmetry is

\[
1 - \frac{|d_\text{rise} - d_\text{fall}|}
         {d_\text{rise} + d_\text{fall}}.
\]

Duration and period use configured time when present and observation positions
otherwise. Parallel `*_samples` fields always retain observation-space values.
Peak and mean phase rates are positive magnitudes except that Transition mean
rate remains signed.

## Accumulation

Accumulation is a dependent object bounded by an existing oscillation identity.
Its `accumulation_id` equals its explicit `parent_oscillation_id`, and parent
completeness is propagated.

For baseline \(b_i\), contribution is

\[
c_i = x_i - b_i.
\]

The baseline may be a scalar, a column, an aggregation within each parent
wave, or a per-signal mapping. Contributions are signed; negative values are
retained rather than clipped.

Without a time column, total area is the deterministic sample sum of
contribution. With time, running and total area use trapezoidal integration
over the configured time coordinate. Accumulation before and after the peak,
area at peak, mean and peak rate, centroid, symmetry, and half-accumulation
time are derived within the parent identity.

The beta implementation requires the oscillation-enriched feature frame as
input. It does not silently reconstruct missing parent waves.

## Missing and partial observations

Missing signal values are preserved. They interrupt Transition classification
and can therefore prevent a complete higher-order object from forming.
FeatureGraph does not interpolate implicitly.

Partial objects carry `is_complete=False`. Default summaries exclude them;
`include_partial=True` retains them for diagnosis. Objects never cross group
boundaries.

## Determinism and provenance

Given identical ordered observations and constructor parameters, FeatureGraph
produces identical feature columns, identifiers, object tables, and queries.
Every `BehaviorObjects` result retains the construction parameters needed to
identify the procedure.
