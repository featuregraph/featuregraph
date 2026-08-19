# From Observations to Inspectable Behavioral Objects: The FeatureGraph Framework

**Nazia Habib**  
Draft research record

## Abstract

Time-series analysis often moves directly from sampled measurements to predictions or aggregate features, leaving the temporal entities used in scientific reasoning implicit. FeatureGraph is a framework for constructing explicit, bounded behavioral objects from ordered observations. A researcher specifies the signal, preprocessing, state predicates, boundary events, object identity, properties, and validation contract. Deterministic computation then produces observation-, event-, and object-level tables with preserved provenance and incomplete-boundary status. We demonstrate the framework in two unrelated domains. In BIDMC respiratory waveforms, a frozen rolling-envelope construction produces trough–peak–trough respiratory-cycle objects and is evaluated across 53 records against an independently recorded comparator and two annotation series. In Tennessee Eastman Process simulations, a frozen reactor-pressure construction produces peak events and peak-to-peak cycles that replicate across ten Fault 2 runs and separate those runs from matched normal-operation windows, while correctly revealing that pressure alone is not Fault 2-specific. These studies support FeatureGraph as a representation layer: it preserves researcher-authored semantics, enables transfer tests, and makes both successful structure and failure boundaries inspectable without treating object construction as autonomous scientific judgment.

## 1. Introduction

Scientists commonly reason about entities that are not directly present in raw data: breaths, excursions, transitions, cycles, recoveries, and accumulated episodes. A time-series table contains observations, but these behavioral objects must be constructed. Conventional feature engineering often compresses a window into statistics before defining what the window represents. End-to-end models may learn useful internal representations, but their temporal boundaries and scientific meaning are generally unavailable for inspection.

FeatureGraph begins from a different premise: define the behavioral object before calculating its properties. The framework converts ordered measurements into explicit states, events, bounded objects, and relations. It does not decide that a signal is oscillatory, choose which peak matters, or infer that an excursion diagnoses a fault. Those are scientific choices supplied and tested by the researcher.

This paper asks whether one framework can preserve this construction process across domains without collapsing domain-specific meaning. We examine two cases: respiratory cycles in clinical waveform data and reactor-pressure cycles in an industrial simulation. The domains use different signals, preprocessing, validation evidence, and interpretations, but share the same representational operations.

## 2. Framework

FeatureGraph preserves three layers:

1. **Observations:** time-indexed raw and derived signals.
2. **States and events:** sample-level predicates and discrete boundary markers.
3. **Objects:** one row per bounded behavior, with intrinsic properties, provenance, completeness, and optional relations.

For a processed signal \(s_t\), a simple directional construction defines

\[
\Delta s_t = s_t - s_{t-1},
\]

\[
R_t = [\Delta s_t > \epsilon], \quad
F_t = [\Delta s_t < -\epsilon], \quad
I_t = [|\Delta s_t| \leq \epsilon].
\]

Entering or exiting a state creates an event. For example, a valid transition from rising to non-rising can define a peak event:

\[
P_t = R_{t-1} \land \neg R_t.
\]

Cumulative boundary counts assign identity to intervals, while an explicit interval convention determines which side contains the boundary. Grouped aggregation then derives properties implied by the object definition, such as duration, amplitude, period, phase symmetry, or prominence. First and final fragments remain represented but are marked incomplete.

### 2.1 Researcher-input and generated-study workflow

Each study is represented by two notebooks. The researcher-input notebook is the scientific contract. It records the study scope, selected parameters, preprocessing, state and event definitions, object identity, requested properties, validation requirements, supported claims, unsupported claims, and unresolved choices. The generated-study notebook implements those mechanics, adds structural assertions and provenance, and produces the requested tables.

This division is designed for human–AI research workflows. Automated generation may translate an explicit contract into executable code, but it must not silently add persistence, hysteresis, merging, exclusion, or interpretation rules. When the researcher has not defined completeness or diagnostic meaning, the generated output must retain candidates or fragments rather than promote them to validated objects.

### 2.2 Validation

Structural validation precedes domain validation. Required checks include monotonic time, isolation between groups, preservation of raw values, mutually exclusive states on valid observations, absence of events across invalid boundaries, complete assignment of observations, consistent event order, and explicit incomplete fragments.

Domain validation then asks whether the same frozen construction transfers. Parameters selected on a development record are applied unchanged to held-out records. Comparator agreement, annotations, normal controls, or contrasting conditions provide evidence appropriate to the domain. Failure under transfer is retained as a result rather than repaired through undocumented record-specific tuning.

## 3. Case Study 1: BIDMC Respiratory Cycles

The BIDMC study constructs respiratory-cycle objects from waveform observations sampled at 125 Hz. A fixed envelope is produced by a 100-sample rolling maximum followed by a 100-sample rolling mean and an offline alignment shift. Directional states are derived from the one-sample envelope difference. State transitions define troughs and peaks, and complete objects follow a trough–peak–trough contract. Raw respiration is retained for amplitude and accumulation measurements; envelope values determine boundaries.

The construction was developed on subject 1 and applied unchanged to all 53 BIDMC records. An independently documented comparator—selected in a context-isolated language-model workflow and preserved for execution without further model access—provided a second object table. Two BIDMC breath-annotation series provided additional event-level evidence.

Across 53 records, FeatureGraph produced 8,180 complete objects and the comparator produced 7,168. One-to-one temporal matching paired 6,513 objects, leaving 1,667 FeatureGraph-only and 655 comparator-only objects. Median subject-level matched fractions were 88.8% for FeatureGraph objects and 100.0% for comparator objects. The envelope improved transfer relative to the earlier difference rule, particularly in object count and temporal-symmetry agreement, but did not establish universal equivalence. Subjects 5, 35, 38, and 39 remained severe failure cases, and subject 39 had no matched comparator objects under the frozen tolerance.

The result is therefore not that FeatureGraph autonomously recognizes breathing. The result is that a researcher-defined cycle representation can be executed reproducibly, compared at the object level, transferred across records, and inspected where its boundary semantics fail.

## 4. Case Study 2: TEP Reactor-Pressure Cycles

The Tennessee Eastman Process study uses Fault 2, simulation run 10, as the development record. Reactor pressure is transformed by a 50-sample rolling maximum, a 50-sample rolling mean, and `shift(-50)` for offline alignment. Rising, falling, and inactive states follow the sign of the aligned pressure rate. Valid exits from rising define peak events. Half-open intervals \([P_i, P_{i+1})\) define peak-to-peak cycle objects; leading and trailing fragments are retained as incomplete.

On the development run, the construction produced 32 valid peak events, 31 complete cycles, and two boundary fragments. All structural checks passed. The dominant aligned peak occurred at index 637 (10.62 hours) with pressure 2806.58.

The frozen construction was then applied to the other nine Fault 2 runs. Every run produced a dominant peak between indices 630 and 687. Maximum aligned peak pressure ranged from 2804.96 to 2807.60. For negative controls, the 500-hour normal Mode 1 record was divided into ten non-overlapping 50-hour windows. All ten Fault 2 runs exceeded all ten normal windows in maximum aligned peak pressure and peak excess over the run median. Prominence and peak-event count did not separate the cohorts.

A specificity check applied the same construction to simulation run 10 from the other 20 fault classes. Ten fault classes equaled or exceeded Fault 2 run 10 in peak excess. Faults 1 and 7 also produced large early peaks near the Fault 2 event time. The representation therefore identifies a repeatable Fault 2-associated abnormal pressure response and separates it from normal operation in this cohort, but reactor pressure alone does not identify the disturbance as Fault 2.

This negative specificity result is evidence of representational fidelity. The object table exposes what the signal supports—an abnormal pressure excursion—and prevents a stronger diagnostic claim that the transferred evidence does not support.

## 5. Discussion

The two studies share invariant mechanics while preserving different scientific meanings. Both retain raw observations, construct a separate processed signal, derive directional states, locate transition events, assign bounded identity, summarize object properties, retain fragments, and test frozen transfer. BIDMC objects are clinically interpretable respiratory cycles validated against comparator objects and annotations. TEP objects are industrial pressure cycles validated against repeated simulations, normal operation, and contrasting faults.

Three implications follow.

First, behavioral objects can provide a stable interface between raw data and reasoning. A downstream model or analyst can query objects, their supporting observations, and their relationships without reconstructing boundaries from plots.

Second, transfer belongs in the object definition process. A construction that works only on its development trace remains a local encoding. Applying unchanged rules across groups reveals whether the representation is stable, over-segmented, under-sensitive, or dependent on unrecorded intervention.

Third, representation and diagnosis should remain distinct. FeatureGraph can faithfully construct a pressure excursion that is associated with several faults. Diagnostic specificity may require relations among objects from multiple signals—for example, a Stream 4 composition transition preceding a pressure excursion and controller recovery. The pressure object need not be redesigned merely because it is insufficient alone.

## 6. Limitations

Both case studies use researcher-selected signals and preprocessing, so neither demonstrates autonomous discovery of behavioral semantics. BIDMC transfer remains uneven across irregular records, and comparator matching depends on an explicit tolerance and matching contract. The TEP normal controls are windows from one continuous 500-hour record rather than independent normal simulations. Cross-fault specificity currently uses one matched run per contrasting class. The offline alignment operations use future observations; causal deployment would require separate event and detection times. Finally, two domains establish a useful cross-domain demonstration but not universal applicability.

## 7. Conclusion

FeatureGraph represents temporal behavior by turning observations into explicit states, events, and bounded objects under a researcher-authored contract. Across BIDMC respiration and Tennessee Eastman reactor pressure, frozen constructions produced inspectable objects, transferred beyond their development records, and preserved both successful structure and failure boundaries. The framework’s central contribution is not a new peak detector or fault classifier. It is a durable representation layer in which scientific choices, object boundaries, properties, provenance, and unresolved claims remain available for inspection and further reasoning.

## Data and reproducibility note

The repository contains the researcher-input notebooks, generated-study notebooks, structural validation code, and the recorded TEP transfer results. Dataset citations and a formal related-work section should be added before submission.
