### 1.1 Representation success, empirical adequacy, and transfer

A representation can be evaluated using four criteria:

- Execution success: does FeatureGraph apply the declared contracts deterministically and reproduce the saved outputs?
- Representational adequacy: are distinct temporal meanings retained rather
  than collapsed into one index or discarded as malformed?
- Empirical adequacy: does the resulting representation satisfy the evaluation criteria on the data for which it was developed?
- Transfer: can the same frozen representation produce adequate objects and measurements on new records?

## 2. Representation

An analysis of a sampled time-series signal can be decomposed into the following parts.

### 2.1 Observed data

This consists of:

- sampled values and their ordering.

### 2.2 Representation frame

This consists of:

- the physical units in which a signal is expressed;
- its sampling interval and temporal resolution;
- recording duration and coverage;
- normalization and smoothing applied to the signal; and
- sensor resolution and preprocessing.

The representation frame specifies the context that must be recorded to
interpret and compare measurements from the signal while retaining information
needed for analysis.

### 2.3 Construction contract

This consists of:

- rules that identify states, transitions, boundaries, and objects.

The FeatureGraph position is: if observed signal morphology can be described
in a contract that can then be used to identify corresponding characteristics
in multiple signals, the analytical procedure has become durable, inspectable,
and testable for transfer.

### 2.4 Measurement contract

This consists of:

- rules specifying how characteristics such as amplitude, rate of change,
  symmetry, and accumulation are calculated.

### 2.5 Construction and measurement contracts

FeatureGraph as described provides two contracts:

1. A construction contract that specifies states, transition events, boundaries, and objects. The vocabulary used to define states and transitions is deliberately kept small. It places defined limits on:

   - the number of possible states that will be identified
   - the number of transition events that will be identified
   - the construction process for measured properties

2. A measurement contract that provides specifications for obtaining amplitude, rates of change, symmetry, accumulation, and other calculated properties of derived objects.

These two contracts preserve different analytical decisions. The construction
contract determines whether an object exists, its identity, boundaries,
landmarks, and membership in the object set. The measurement contract operates
on the constructed object and determines how its properties are calculated.

The BIDMC study identified several areas where these contracts must remain
distinct:

**Construction contract:**

- disagreements over accepted cycle and object boundaries

**Measurement contract:**

- half-range vs full-excursion amplitude difference, a definition that concerns the measurement contract. Amplitude needs to be defined consistently, which is part of the measurement contract

**Both contracts:**

- wave symmetry: its formula is a measurement choice but its value depends on boundary landmarks determined by the construction contract
- a transition boundary can mark the start or end of an extremum interval,
  while a conventional comparison may require a projected point such as the
  interval midpoint

### 2.6 Semantic or physical context

This consists of:

- what the signal represents;
- which physical mechanism produced it;
- what domain it belongs to; and
- what causal meaning and structure the engineer believes it contains.

Semantic context explicitly exists outside the scope of FeatureGraph.
FeatureGraph is not asked to understand what a signal means in the real world
to an observer or researcher. It may retain user-supplied labels and metadata,
but object construction does not depend on FeatureGraph inferring their
physical or domain meaning.

### 2.7 Evaluation criteria: durability, inspectability, and transfer

A representation system can convert analytical decisions that were implicit in an LLM-assisted workflow into an explicit, executable contract. The quality of the representation can be measured using the following criteria:

#### 2.7.1 Durability

Can the same declared analysis be executed later without the LLM? The analysis should produce reproducible objects from the constructed contract on frozen inputs.

#### 2.7.2 Inspectability

Can a human see and revise how states, boundaries, objects, and measurements were defined? A human should be able to modify and rerun the code, edit its assumptions and contract, and identify structural limitations with the representation.

#### 2.7.3 Transfer

Does the same contract produce useful objects on new data without case-specific modification? We can measure this in:

- whether the contract runs unchanged;
- whether it produces structurally valid objects; and
- whether those objects agree with an independent reference or annotation.

### Construction contract

FeatureGraph begins with ordered observations and constructs explicit temporal structures from relationships among those observations. This requires separating three representational layers:

- the observed signal
- sample-level states and events constructed from the signal
- bounded objects constructed from those events

Let `x_t` denote the observed signal at sample `t`. A construction signal is introduced to expose behavior at the temporal scale relevant to the analysis. For the respiration signal, the construction signal is an upper envelope:

$$
s_t^{(w)}
=
\operatorname{shift}_{-w}
\left[
\operatorname{mean}_w
\left(
\operatorname{max}_w(x)
\right)
\right]_t
$$

where w is the declared envelope window. The local direction of the envelope creates three primitive states:

$$
R_t = \mathbf{1}\left(s_t^{(w)} - s_{t-1}^{(w)} > 0\right),
$$

$$
F_t = \mathbf{1}\left(s_t^{(w)} - s_{t-1}^{(w)} < 0\right),
$$

$$
I_t = \mathbf{1}\left(s_t^{(w)} - s_{t-1}^{(w)} = 0\right).
$$

These states mean that the constructed wave is rising, falling, or inactive at a particular sample. 

# add in enter/exit events


## Object schema

| Field                            | Purpose                    |
| -------------------------------- | -------------------------- |
| `subject_id`, `peak_id`          | Stable identity            |
| `start_peak_time`                | Left boundary              |
| `trough_time` or trough interval | Internal turn              |
| `end_peak_time`                  | Right boundary             |
| `period_seconds`                 | Cycle duration             |
| `rising_seconds`                 | Rising-state duration      |
| `falling_seconds`                | Falling-state duration     |
| `peak_inactive_seconds`          | Peak plateau               |
| `trough_inactive_seconds`        | Trough pause               |
| `is_complete`                    | Both boundaries present    |
| `is_structurally_valid`          | Expected state/event order |
| `ambiguity_reason`               | Preserves abnormalities    |
| `smooth_window_seconds`          | Construction provenance    |


## Measurement contract


