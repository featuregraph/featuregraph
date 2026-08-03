## Framework

FeatureGraph is a deterministic framework for transforming ordered observations into explicit behavioral objects. Its purpose is to expose temporal structures that are present in a signal but are not directly represented by the observations themselves. A time series records values at successive positions; it does not ordinarily identify where a behavior begins, how long it persists, when it changes direction, or which observations belong to the same occurrence. These distinctions must be constructed before they can be measured or queried.

The framework separates this construction into three representational levels:

1. ordered observations;
2. sample-level states and events;
3. temporally bounded behavioral objects.

Each level preserves information required by the next. Observations provide the measured values. States and events describe the local behavioral condition of each observation and mark changes between conditions. Behavioral objects bind related states and events into identifiable occurrences with explicit boundaries and measurable properties.

This separation is central to the framework. A duration, amplitude, or accumulation is not treated as an isolated feature calculated directly from an arbitrary window of samples. It is treated as a property of a particular behavioral object. The object establishes which observations belong together and therefore supplies the context in which the property is defined. The resulting representation supports both conventional statistical analysis and object-level questions such as how many behaviors occurred, which were incomplete, which persisted unusually long, and how their properties varied across groups or signals.

***The goal of this project is to define behavioral objects rigorously enough and with enough generality that they can be reproduced by non-human computation layers and used for downstream processing. The current implementation allows for object-level querying.***

### Ordered observations

Let an observed signal be an ordered sequence

[
X = {(t_i, x_i)}_{i=1}^{n},
]

where (t_i) denotes an ordered position or timestamp and (x_i) denotes the observed value. FeatureGraph requires the observations to be ordered but does not require that the ordering variable represent uniformly spaced physical time. When observations are uniformly sampled, differences in index positions can be interpreted as sample durations and converted to physical time using the sampling interval. When sampling is irregular, duration must instead be calculated from the corresponding timestamps.

An observation is not itself a behavioral object. It is evidence from which behavioral distinctions may be constructed. A single value generally does not determine whether a signal is rising, falling, oscillating, or accumulating. Such classifications depend on comparisons among observations and on rules chosen for the process under study.

The framework therefore does not assume that raw observations contain a universal or self-evident set of behaviors. A researcher specifies an operational construction appropriate to the signal, including such choices as the comparison lag, tolerance for negligible change, grouping variables, and optional smoothing. Once supplied, these choices define a reproducible transformation. Given the same ordered observations and construction parameters, FeatureGraph produces the same states, events, objects, and measurements.

This determinism distinguishes behavioral construction from an informal visual interpretation of a signal. A researcher may recognize cycles by inspection, but that recognition does not by itself provide executable rules for assigning every observation to a cycle. FeatureGraph requires those rules to be stated in a form that can be applied consistently across the complete sequence.

### Sample-level states

A state is a Boolean predicate evaluated at each observation. It indicates whether a defined behavioral condition holds at that position. For example, the direction of change in a signal may be represented using rising and falling states. Given a comparison lag (l) and a tolerance (\epsilon), a directional difference may be written as

[
\Delta_l x_i = x_i - x_{i-l}.
]

The corresponding sample-level states are

[
R_i = \mathbb{1}(\Delta_l x_i > \epsilon)
]

and

[
F_i = \mathbb{1}(\Delta_l x_i < -\epsilon),
]

where (R_i) indicates a rising condition and (F_i) indicates a falling condition. Observations whose absolute difference does not exceed (\epsilon) may be treated as locally unchanged, depending on the construction used.

These definitions illustrate the role of parameters in FeatureGraph. The lag determines the temporal scale over which change is evaluated. The tolerance determines which changes are behaviorally meaningful. Smoothing may suppress local reversals before state construction. These operations affect the behavioral representation and must therefore be recorded as part of its provenance.

States are intentionally local. A rising state asserts that a directional condition holds at an observation; it does not assert that the observation belongs to a complete oscillation. The distinction prevents local evidence from being conflated with a higher-order behavioral interpretation. Object construction occurs only after the state sequence has been made explicit.

States also need not be limited to directional change. Other processes may be represented using conditions such as above threshold, below threshold, active, inactive, increasing rapidly, or within a specified range. What makes these predicates states within the framework is not their domain vocabulary but their role: each converts ordered observations into an explicit sample-level condition that can be entered, exited, grouped, and composed.

### Events and boundaries

An event marks a change in a state. For a Boolean state (S_i), an entry event occurs when the state changes from false to true:

[
E^{\mathrm{in}}_i(S)
====================

\mathbb{1}(S_i = 1 \land S_{i-1} = 0).
]

An exit event occurs when the state changes from true to false:

[
E^{\mathrm{out}}_i(S)
=====================

\mathbb{1}(S_i = 0 \land S_{i-1} = 1).
]

States describe persistence; events describe change. A state may remain true over many observations, whereas its entry and exit each occur at a boundary. This distinction permits the framework to represent both that a behavior is occurring and when its occurrence begins or ends.

Events provide candidate landmarks for constructing behavioral objects. In an oscillatory signal, for example, a change from falling to rising can identify a trough region, while a change from rising to falling can identify a peak region. These landmarks are not imposed as independent peak detections. They are derived from transitions in the explicit state sequence.

Boundary semantics depend on the state definition and preprocessing choices. If a lagged difference or smoothing window is used, a detected reversal may be displaced relative to the extremum of the unprocessed signal. The resulting boundary remains reproducible, but its interpretation is tied to the declared construction. FeatureGraph therefore treats the parameters and intermediate states as part of the evidence for an object rather than hiding them behind its final measurements.

Events must also respect group boundaries. If a dataset contains multiple subjects, trials, machines, or simulation runs, the first observation in one group cannot complete a state transition begun in another. State changes, event identities, and object identifiers are consequently calculated independently within each group.

### Behavioral objects

A behavioral object is a temporally bounded occurrence constructed from an ordered configuration of states and events. It has an identity, a beginning, an end, and a set of observations associated with that interval. Once these elements have been made explicit, properties can be calculated for the occurrence rather than for an unstructured collection of samples.

Let (O_j) denote the (j)-th object:

[
O_j = (b_j, e_j, I_j, P_j),
]

where (b_j) is its starting boundary, (e_j) is its ending boundary, (I_j) is the set of observations assigned to the object, and (P_j) is a collection of derived properties. An object may additionally contain internal landmarks, such as a peak separating rising and falling phases.

Object identity is essential. Without an identifier, a collection of boundary and property columns remains difficult to address computationally. Assigning an identifier makes it possible to group all samples belonging to the same occurrence, summarize the occurrence as one row, relate it to other objects, and retrieve it through a query.

The alpha implementation realizes this construction most fully for oscillations. An oscillation is represented as a trough–peak–trough sequence composed of a rising phase followed by a falling phase. The initial trough defines the start of an occurrence, the directional reversal defines its peak, and the subsequent trough defines its end. Each valid sequence receives an object identifier, and all observations between its boundaries are associated with that oscillation.

This definition converts a repeating waveform into a table of distinct occurrences. A signal containing hundreds of cycles is no longer represented only as thousands of sample values. It is also represented as hundreds of rows, each corresponding to one bounded oscillation.

Object completeness is evaluated structurally. An object is complete only when the events and landmarks required by its definition are present. An occurrence beginning near the left boundary of an observed sequence may lack evidence of its true start. An occurrence continuing beyond the right boundary may lack its closing event. Such occurrences should not silently receive the same status as objects whose full construction is observed.

Completeness is therefore a property of the available evidence, not a judgment about whether the physical behavior itself was complete. The behavior may have continued outside the observation interval. FeatureGraph records only whether the data contain the boundaries required by the object definition.

### Object properties

Once an object has been bounded, its properties can be calculated from the observations and landmarks assigned to it. For an oscillation with start (b_j), peak (p_j), and end (e_j), the rising and falling durations are

[
d^{\mathrm{rise}}*j = t*{p_j} - t_{b_j}
]

and

[
d^{\mathrm{fall}}*j = t*{e_j} - t_{p_j}.
]

Its total duration is

[
d_j = d^{\mathrm{rise}}_j + d^{\mathrm{fall}}_j.
]

In the alpha implementation, amplitude is defined as half the observed range within the object:

[
a_j =
\frac{
\max_{i \in I_j}(x_i)
---------------------

\min_{i \in I_j}(x_i)
}{2}.
]

Temporal symmetry expresses the relative balance between the rising and falling phases. One possible normalized form is

[
s_j =
\frac{
d^{\mathrm{rise}}_j - d^{\mathrm{fall}}_j
}{
d^{\mathrm{rise}}_j + d^{\mathrm{fall}}_j
}.
]

Values near zero indicate similar rising and falling durations, while positive or negative values indicate temporal imbalance. The precise sign interpretation follows the order of terms in the implementation.

These measurements are ordinary mathematical quantities. The contribution of the framework is not a new formula for duration or amplitude. It is the construction of the object to which those formulas are applied. The framework supplies the identity, boundaries, internal landmarks, and membership needed to calculate the measurements reproducibly.

This organization also separates sample-level evidence from object-level output. The expanded representation retains states, events, and identifiers alongside the observations. The summary representation contains one row per object and exposes its principal boundaries and properties. The former supports inspection and provenance; the latter supports analysis and querying.

### Composition and accumulation

Behavioral objects may provide the interval over which a second construction is defined. The alpha implementation demonstrates this through wave-derived accumulation. Rather than treating accumulation as an independent detector, it calculates accumulated quantity within the boundaries of an oscillation.

For an oscillation (O_j), let (c_j) denote a baseline, defined in the alpha implementation from the observed values within that wave. The contribution above baseline is

[
q_i = x_i - c_j,
\qquad i \in I_j,
]

with the construction restricted as appropriate to nonnegative contribution. Cumulative accumulation through position (k) is then

[
A_{j,k}
=======

\sum_{\substack{i \in I_j \ i \leq k}}
q_i \Delta t_i.
]

The final value (A_{j,e_j}) gives the total accumulated quantity associated with the oscillation. Additional properties can be derived from the same cumulative trajectory, including accumulation before and after the peak, the time required to reach half of the total, the time of maximum accumulation, accumulation rate, and temporal centroid.

This construction illustrates a general compositional principle: one behavioral representation may supply the boundaries or context required to construct another. The accumulation is interpretable because it belongs to an identified interval. Its value can be related to the oscillation’s amplitude, duration, symmetry, subject, or experimental group.

The alpha implementation demonstrates only this wave-derived form of accumulation. It does not establish that every accumulation process must be defined by an oscillation, nor does it provide a universal accumulation detector. Its purpose here is to show that explicit object boundaries permit additional behavioral quantities to be constructed and related without returning to arbitrary sample windows.

### Summary tables and queries

The final object table is the primary computational interface produced by the framework. Each row represents one occurrence, and each column represents an identity field, boundary, structural landmark, property, completeness indicator, or grouping variable. A typical oscillation summary contains fields such as

[
{\text{object ID},,
\text{start},,
\text{peak},,
\text{end},,
\text{rise duration},,
\text{fall duration},,
\text{duration},,
\text{period},,
\text{amplitude},,
\text{temporal symmetry},,
\text{completeness}}.
]

This representation changes the level at which the signal can be interrogated. A sample-level question asks for observations satisfying a condition. An object-level question asks for occurrences satisfying a behavioral condition. Examples include:

* How many complete oscillations occurred?
* Which oscillations lasted longer than a specified duration?
* What fraction exceeded an amplitude threshold?
* Which objects had strongly asymmetric rising and falling phases?
* How did object properties differ between subjects or simulation runs?
* Which oscillations accumulated most of their total quantity before the peak?

These queries do not require the analyst to reconstruct object boundaries each time. Construction is performed once, and subsequent operations consume the resulting object representation. Because the summaries are ordinary tables, they can be filtered, grouped, joined, visualized, or supplied to downstream statistical and machine-learning systems using existing data tools.

This queryability is not merely a convenience. It is the computational consequence of making behavioral identity explicit. An algorithm cannot reliably request “long oscillations” from an undifferentiated series unless some earlier process has defined what an oscillation is, identified its boundaries, and measured its duration. FeatureGraph externalizes that prerequisite work into a reusable representation.

### Scope of the framework

FeatureGraph does not claim to infer every meaningful behavior from observations without prior specification. The framework begins after a behavioral distinction has been operationally defined. It provides a procedure for expressing that distinction as states and events, constructing bounded occurrences, measuring their properties, and exposing the results to other computational processes.

The alpha version establishes this procedure through oscillatory signals and wave-derived accumulation. It demonstrates that the same construction can be applied to signals from unrelated domains while preserving a common object schema. The semantics of the underlying systems remain different: a respiratory cycle is not physically equivalent to a reactor-temperature cycle. What is shared is the computational organization of repeated directional behavior into bounded objects with comparable structural properties.

The framework therefore separates domain meaning from behavioral structure. Domain expertise determines which signal and construction are scientifically meaningful. FeatureGraph determines how the declared construction is applied consistently, how its evidence is retained, and how the resulting occurrences are represented.

The central output is not a transformed signal or a collection of disconnected features. It is an explicit behavioral record: a set of identifiable objects grounded in ordered observations, supported by sample-level states and events, bounded in time, measured consistently, and available for computational query.
