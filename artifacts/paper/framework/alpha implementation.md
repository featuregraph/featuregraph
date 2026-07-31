## Alpha implementation

The alpha implementation of FeatureGraph (`v0.1.0a1`) realizes the framework as a deterministic Python package built on pandas. It provides two behavioral constructors: `Oscillation`, which converts one or more ordered signals into bounded oscillation objects, and `Accumulation`, which constructs baseline-relative accumulation objects within the wave boundaries supplied by the oscillation representation. The implementation also provides a common construction pipeline, a container for retaining object tables and their supporting evidence, and a small query interface for filtering and selecting object-level records.

The implementation is tied to the archived `v0.1.0a1` release. The current development branch is not API-compatible with this release and was not used to produce the alpha results reported in this paper.

### Software organization

Both alpha constructors inherit from an abstract `Behavior` class. The base class standardizes the construction sequence:

1. validate the signal and grouping columns;
2. optionally derive a working signal;
3. construct sample-level primitives;
4. assign behavioral-object identifiers;
5. calculate row-aligned measurements.

These stages are executed by `fit_transform()`, which copies the input DataFrame before applying the transformations. The original input is therefore not modified in place. The returned DataFrame preserves the observations and adds the states, events, identifiers, landmarks, and measurements used during construction.

Object summarization is a separate operation. After calling `fit_transform()`, the user calls `summarize()` for a configured signal. This separation leaves the sample-level representation available for inspection while producing a compact table with one row per behavioral object. It also makes the relationship between the final measurements and the evidence from which they were calculated explicit.

A constructor accepts either one signal name or a sequence of signal names. Grouping may be absent, may use one column, or may use several columns. Where grouping is supplied, differences, events, identifiers, and summaries are calculated independently within each group. This prevents a subject, trial, or simulation run from inheriting a state transition or object boundary from the preceding group.

### Oscillation construction

The alpha `Oscillation` constructor accepts the signal specification and grouping columns together with four construction parameters: whether smoothing is enabled, the smoothing-window length, the lag used to calculate directional differences, and a nonnegative tolerance (epsilon). The implementation validates that the smoothing window and difference lag are at least one and that (epsilon) is nonnegative.

When smoothing is enabled, a grouped rolling-mean signal is added and used for subsequent numerical construction. The original signal remains in the feature table. When smoothing is disabled, the observed signal itself is used. For a working signal (x), the implementation calculates the lagged difference

[
Delta_l x_i = x_i - x_{i-l}.
]

For grouped data, this difference is evaluated within each group. Two Boolean directional states are then constructed:

[
R_i = mathbb{1}(Delta_l x_i > epsilon)
]

and

[
F_i = mathbb{1}(Delta_l x_i < -epsilon).
]

The alpha implementation derives boundary events from the rising state. An entry event marks a change into the rising state, and an exit event marks a change out of it. Because the directional state describes the edge ending at the current row, a reversal observed at row (i) places the corresponding extremum at the preceding sample. The implementation therefore shifts each rising-state entry back one sample to mark a trough and shifts each rising-state exit back one sample to mark a peak. Peak and trough indices are retained as columns in the feature table.

A wave identifier is assigned from the cumulative count of rising-state entry events. Within each group, observations following the same entry event receive the same identifier. The resulting interval is intended to represent a trough–peak–trough sequence: the first trough provides the start boundary, a subsequent peak provides the internal reversal, and the last trough provides the end boundary.

For each wave identifier, the implementation calculates row-aligned measurements from all observations assigned to that identifier. These include counts of rising and falling samples, the maximum and minimum working-signal values, amplitude, duration, mean rising and falling rates, and peak rising and falling rates. The local rate is the lagged difference divided by the difference lag:

[
r_i = rac{Delta_l x_i}{l}.
]

The peak rising rate is the largest nonnegative local rate within the wave. The peak falling rate is reported as the positive magnitude of the most negative local rate.

### Completeness and object boundaries

The alpha implementation distinguishes structurally complete waves from partial waves. A wave is marked complete only if it contains evidence of a rising-state entry, has nonmissing start, peak, and end indices, satisfies

[
b_j < p_j < e_j,
]

and is not the final wave identifier within its group. Excluding the final identifier ensures that an apparent closing trough is supported by the subsequent entry event rather than inferred from the end of the observed sequence.

This rule concerns completeness of the observed construction evidence. It does not assert that an incomplete physical oscillation occurred. A partial object may instead reflect truncation at the beginning or end of the recorded sequence or insufficient evidence under the selected parameters.

By default, `summarize()` removes incomplete waves. The optional `include_partial=True` argument retains them and exposes their completeness indicator. Thus, partial constructions remain inspectable without being silently combined with complete objects in the default object table.

The oscillation summary is produced by grouping the feature table by the user-supplied grouping columns and the wave identifier. The summary retains the first trough index as the start, the maximum peak index as the peak, and the maximum trough index as the end. It then calculates

[
d^{mathrm{rise}}_j = p_j - b_j,
]

[
d^{mathrm{fall}}_j = e_j - p_j,
]

and

[
d_j = e_j - b_j.
]

These quantities are expressed in index units. For uniformly sampled signals they can be converted to physical time using the sampling interval.

Period is calculated as the difference between consecutive peak indices within each group. Amplitude is half the range of the working signal within the object:

[
a_j = rac{max(x_i)-min(x_i)}{2},
qquad i in I_j.
]

Mean rising and falling rates divide the same within-object range by the corresponding phase duration. Temporal symmetry is implemented as

[
s_j =
1 -
rac{
left|d^{mathrm{rise}}_j-d^{mathrm{fall}}_jight|
}{
d_j
}.
]

This measure equals one when the two phase durations are equal and approaches zero as one phase occupies nearly the entire object duration. Unlike a signed asymmetry measure, it records the degree of balance but not which phase is longer.

The resulting oscillation table contains the grouping variables and the fields `oscillation_id`, `is_complete`, `start_index`, `peak_index`, `end_index`, `rise_duration`, `fall_duration`, `duration`, `period`, `amplitude`, `rising_mean_rate`, `falling_mean_rate`, `peak_rise_rate`, `peak_fall_rate`, and `temporal_symmetry`.

### Wave-derived accumulation

The alpha `Accumulation` constructor does not independently detect accumulation intervals. It requires the wave identifiers produced by `Oscillation` and constructs one accumulation object inside each identified wave. Accumulation is therefore compositional in this implementation: the oscillation representation supplies its identity and temporal support.

For each signal, a baseline or threshold may be supplied as a numeric constant, the name of an existing column, a pandas groupwise aggregation such as `"min"`, or a signal-specific mapping of these specifications. With the default `"min"` setting, the baseline (c_j) is the minimum observed signal value within wave (j). The contribution at observation (i) is

[
q_i = x_i - c_j.
]

The cumulative accumulation is calculated as the within-wave cumulative sum

[
A_{j,k} = sum_{substack{i in I_j \\ i le k}} q_i.
]

The alpha calculation is sample based: it does not multiply contributions by an explicit sampling interval. Consequently, `total_auc` is a discrete sum in signal-value-by-sample units. For a regularly sampled signal, a physical-time area can be obtained by multiplying by the sampling interval. The implementation permits negative contribution when the selected threshold lies above the signal; it does not clip contributions at zero.

The contribution is additionally classified as accumulating when (q_i>epsilon), depleting when (q_i<-epsilon), and inactive when (|q_i|leqepsilon). The accumulation identifier is copied from the parent wave identifier. Each row also receives a position relative to the start of its accumulation object.

Using the peak event inherited from oscillation construction, the implementation divides contribution into portions before and from the peak. It records the cumulative value at the peak, calculates the total contribution for the wave, and identifies the first within-object position at which the cumulative value reaches at least half of the total. A first moment is calculated by weighting each contribution by its within-object sample position.

Accumulation completeness is inherited from the parent wave. As with oscillations, incomplete objects are excluded by default and may be retained with `include_partial=True`. The summary table contains the object boundaries, duration in samples, baseline, total accumulation, accumulation at the peak, contributions before and from the peak, mean accumulation rate, accumulation symmetry, centroid time, and half-accumulation time.

The mean accumulation rate is

[
ar{A}_j = rac{sum_{i in I_j} q_i}{|I_j|}.
]

Accumulation symmetry is implemented as

[
s^{A}_j =
1 -
rac{
left|Q^{mathrm{before}}_j-Q^{mathrm{from}}_jight|
}{
Q^{mathrm{before}}_j+Q^{mathrm{from}}_j
},
]

when the denominator is positive. The centroid time is the first moment divided by total accumulation. These measures describe the distribution of accumulated contribution within the parent wave rather than a separately detected accumulating episode.

### Returned representation and query interface

Both constructors return a `BehaviorObjects` container from `summarize()`. The container records the behavior type, signal name, object table, complete feature table, grouping columns, declared property names, and construction parameters. Accumulation objects additionally record oscillation as their parent behavior. This structure preserves both representations produced by the pipeline: the compact object-level record used for analysis and the sample-level evidence used to inspect how each object was formed.

`BehaviorObjects.to_pandas()` returns the object table, while `count` and `columns` expose its size and schema. The `query()` method creates a deterministic table query supporting equality and inequality comparisons, membership tests, column selection, ordering, and row limits. Queries are evaluated against already constructed objects. They do not rerun state detection, move boundaries, or recalculate object properties.

The implementation therefore uses pandas for two distinct roles. During construction, grouped vectorized operations convert ordered observations into explicit states, events, identifiers, and measurements. After construction, ordinary table operations consume the resulting behavioral record. This division embodies the framework’s central distinction between defining an occurrence and asking questions about occurrences after their identities and properties have been made explicit.

### Implementation scope

The alpha implementation is a reference realization of the framework for oscillations and oscillation-bounded accumulation. It does not provide universal state discovery, automatic parameter selection, irregular-time integration, or an independent accumulation detector. Its directional construction is sensitive to smoothing, lag, tolerance, sampling characteristics, and noise. These limitations are evaluated separately.

Within this scope, the implementation provides a complete deterministic path from ordered observations to queryable behavioral records. Every object can be traced to its sample-level states and events, every summary is calculated from an explicit object identifier and interval, and the parameters governing construction are retained with the result. This inspectable correspondence between observations, construction evidence, and object tables is the principal software contribution of the alpha release.
