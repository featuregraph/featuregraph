# Representing Respiration Cycles as Explicit Temporal Objects: A FeatureGraph Representation and Transfer Study

**Nazia Habib**  
Working draft, August 2026

## Abstract

Sample-level peak procedures compress several analytical choices into one
operation: which changes constitute events, how extended extrema are located,
where object boundaries fall, and how properties are measured. This study
evaluates whether FeatureGraph can make those choices explicit as durable,
inspectable temporal objects and whether the resulting representation
transfers beyond the record on which it was developed.

The final FeatureGraph construction retains the raw respiration signal for
measurement, constructs candidate-cycle boundaries from a grouped
rolling-maximum/rolling-mean envelope, and represents exact flat extrema as
bounded intervals with deterministic midpoint projections. A frozen SciPy
pipeline originally proposed in a context-isolated large-language-model (LLM)
session serves as an independent point-detector comparator, not as ground
truth. Across all 53 records in the BIDMC PPG and Respiration Dataset, the
plateau-aware construction detected 8,205 peak events and produced 8,133
complete objects. Of 7,168 complete comparator objects, 7,086 matched within
0.5 seconds; 1,047 FeatureGraph-only and 82 comparator-only objects remained.
Median absolute matched-peak error was 6.5 samples, median period error was
0.056 seconds, and median full-excursion error was zero. Forty-seven objects
that point-only logic would have treated as complete were instead retained and
flagged as boundary-ambiguous.

The interval-to-point correction was then frozen prospectively and tested on
the first 20 eligible non-BIDMC MIMIC-II waveform subjects selected by a
deterministic protocol, totaling approximately 160 minutes. Relative to the
same envelope events anchored at plateau leading edges, midpoint projection
preserved all 3,811 detected peaks, increased matches from 2,792 to 2,859,
reduced comparator-only objects from 149 to 82, and reduced median absolute
peak error from 17 to 7 samples. Matches improved on 13 subjects and were
unchanged on seven; none decreased. All four predeclared confirmation criteria
passed.

These results support FeatureGraph as an explicit representation layer: a
single detected event may have a transition time, an extremum interval, and a
projected comparison time without collapsing those meanings. The remaining
FeatureGraph-only objects are concentrated in a minority of BIDMC records and
are preserved as detector-discordant candidate episodes for downstream review.
They prevent a claim of detector equivalence, and neither comparator agreement
nor the unannotated confirmation cohort establishes clinical breath validity.

## 1. Introduction

A time series is sampled as values, but an analysis usually reasons in objects:
cycles, episodes, transitions, extrema, and intervals. Converting samples into
those objects is a representation problem before it is a measurement problem.
A peak can mean the first sample at which rising ceases, an entire flat maximum,
or one point projected from that maximum. If those meanings remain implicit in
code, two methods can appear to disagree even when they identify the same
observed structure.

FeatureGraph is a deterministic representation layer for making such choices
explicit. It separates observed values from states, transition events, bounded
objects, landmark intervals, point projections, and measurement contracts. The
system does not infer that an object is a physiological breath. It executes a
declared construction, preserves partial and ambiguous cases, and emits tables
in which each agreement or disagreement can be located and revised.

Respiration waveforms from critically ill patients provide a demanding case.
Repeated structure is visible, but amplitude scale, clipping, plateaus,
irregular morphology, and measurement artifacts vary substantially among
records. A representation developed on one clean-looking record may therefore
execute perfectly yet transfer poorly. This study asks whether FeatureGraph can
represent candidate trough–peak–trough cycles in a way that remains explicit,
auditable, and transferable across that variation.

The work began with an LLM-proposed SciPy analysis, which is retained as a
frozen comparator and provenance case. That origin is useful but not the main
object of evaluation. The central result is the current FeatureGraph
representation: envelope-derived transition events, interval-valued exact
extrema, deterministic midpoint projections, explicit ambiguity flags, and
object-level transfer evidence.

This representation study contributes:

1. an explicit construction and measurement contract for converting sampled
   respiration into bounded candidate-cycle objects;
2. a distinction among transition anchors, extremum intervals, and projected
   comparison points;
3. a 53-record evaluation of the final plateau-aware representation against a
   frozen SciPy comparator and two manual annotation series;
4. a prospectively frozen confirmation on 20 untouched non-BIDMC MIMIC-II
   source subjects;
5. localization of residual detector-discordant episodes rather than their
   silent removal or automatic classification; and
6. a reproducible provenance record showing how an LLM-originated analysis was
   converted into a durable representation.

### 1.1 Representation success, empirical adequacy, and transfer

A representation can be evaluated using four criteria:

- Execution success: does FeatureGraph apply the declared contracts deterministically and reproduce the saved outputs?
- Representational adequacy: are distinct temporal meanings retained rather
  than collapsed into one index or discarded as malformed?
- Empirical adequacy: does the resulting representation satisfy the evaluation criteria on the data for which it was developed?
- Transfer: can the same frozen representation produce adequate objects and measurements on new records?

The final plateau-aware contract ran deterministically across all 53 BIDMC
records. It retained transition anchors and exact-extremum intervals, marked
ambiguous boundary compositions, and substantially aligned its point
projections with the comparator and annotations. Because that correction was
developed after inspection of BIDMC transfer failures, the 53-record result is
developmental evidence for the final representation. The separate 20-subject
MIMIC-II run froze the correction and its success criteria before detector
outputs were examined; it provides the study's prospective transfer evidence.

Earlier absolute-threshold, MAD-normalized, and hysteresis variants remain in
the record as ablations. They explain why explicit scale and persistence rules
were insufficient, but they do not define the current FeatureGraph result.

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

## 3. Related work

### 3.1 Reproducible computational research and provenance

This study belongs first to the reproducible-computation tradition. Peng
argues that computational results require a reproducible intermediate standard
when full independent replication is unavailable [5]. Sandve et al. turn that
principle into operational rules: retain how every result was produced, avoid
unrecorded manual transformations, archive exact software versions, and keep
the data underlying figures [6]. The FAIR principles broaden the target from
data alone to the algorithms, tools, and workflows that produce them [7].
FeatureGraph follows this line by freezing inputs, parameters, code, object
tables, unmatched cases, and environment metadata.

Workflow systems such as Nextflow make pipelines portable and repeatable [8],
while provenance systems such as noWorkflow recover execution history from
ordinary scripts without requiring a workflow language [9]. Those systems
primarily preserve *how computations executed*. The present work addresses a
complementary layer: preserving the analyst's temporal representation (what
constitutes a state, event, boundary, complete object, and property) so that a
human can inspect and revise the analytical contract rather than merely rerun
the same script. FeatureGraph is not proposed as a replacement for workflow,
environment, or provenance tooling; its object tables and construction records
are intended to compose with them.

### 3.2 LLM-assisted data analysis and human oversight

LLM-based analysis systems demonstrate that models can translate natural
language goals into executable analytical artifacts. LIDA, for example,
decomposes visualization generation into data summarization, goal generation,
code generation, execution, and filtering [10]. WaitGPT exposes generated
analysis code as an interactive visual representation so users can monitor,
verify, and steer individual operations [11]. These systems emphasize access,
generation, and oversight during an active model interaction.

Our question begins after such an interaction: what remains when the model is
unavailable, its conversational context is gone, or a researcher must maintain
the analysis without asking the model to reconstruct its reasoning? The unit of
preservation is therefore not the chat transcript or prose answer. It is a
versioned contract plus executable construction and object-level evidence. The
LLM is neither treated as an oracle nor evaluated as a general-purpose agent;
it is one source of an analytical proposal that must be converted into a
reviewable artifact.

### 3.3 Explicit representation and abstraction

FeatureGraph was also influenced by work that treats representation as central
to generalization. Chollet's formulation of intelligence and the Abstraction
and Reasoning Corpus (ARC) separate task-specific skill from skill-acquisition
and generalization under declared priors [12]. Chollet argues that useful definitions of intelligence must be actionable, explanatory, and measurable, and that task-specific performance must be distinguished from generalization under declared priors and experience. 

This study adopts the evaluation discipline implied by that distinction. FeatureGraph converts researcher-supplied assumptions into explicit construction and measurement contracts, creating conditions in which performance on a development record can be distinguished from transfer of the same contracts to other records. FeatureGraph’s contribution is a durable, auditable representation layer. When the researcher’s assumptions about the observed data are adequate for constructing the intended objects, the representation succeeds empirically. When those assumptions do not remain adequate on new data, the representation fails to transfer.

### 3.4 Time-series representations

Time-series research contains many alternative representations designed for
particular downstream tasks. Symbolic Aggregate approXimation (SAX) reduces a
real-valued sequence to a lower-dimensional symbolic string while preserving a
lower bound on distance for indexing and mining [13]. Shapelets identify
discriminative subsequences that can support interpretable classification [14].
Both demonstrate that the choice of representation determines which operations
and comparisons become tractable.

FeatureGraph differs in objective. It does not seek a compact global encoding
or a discriminative subsequence classifier in this experiment. It constructs a
relational table of temporally bounded candidate objects with explicit starts,
events, ends, completeness, properties, and parent/child relations. Nor is it a
new peak-detection algorithm: the state rule that creates candidate boundaries
is supplied by the researcher. The evaluation therefore asks whether this
object representation preserves and exposes an analysis, and separately
whether the supplied boundary rule transfers.

## 4. Data and study scope

### 4.1 BIDMC study motivation

The BIDMC respiration data were selected because they offer 53 public,
eight-minute recordings, a fixed 125 Hz sampling rate, visible repeated
waveform structure, and two independent manual breath-annotation series. The
researcher did not begin with domain expertise in respiratory physiology.
This made the dataset appropriate for studying analytical preservation and
representation, but it also limits the interpretation: this is not a clinical
validation study and no detected quantity is claimed to measure calibrated
airflow or volume.

### 4.2 Dataset and evaluation scope

The [BIDMC PPG and Respiration Dataset](https://physionet.org/content/bidmc/1.0.0/)
contains 53 recordings extracted from critically ill patients, with
physiological signals sampled at 125 Hz and two sets of manually annotated
breath sample numbers. Each record is approximately eight minutes long. This
study uses the impedance respiration waveform and the two annotation columns.

Subject 1 served as the initial development record. The first comparator,
FeatureGraph construction, threshold selection, and object-contract
harmonization were performed on this record. Subjects 2–53 were initially
treated as a frozen transfer cohort. The envelope and plateau representation
was subsequently developed from the 53-record evidence and is therefore
reported as a final-representation evaluation rather than an untouched test.

Prospective confirmation used the MIMIC-II matched waveform archive from which
the curated BIDMC records were derived. All 53 curated source-subject IDs were
excluded before scanning. Remaining subject directories were considered in
lexicographic order, with one eight-minute RESP window selected only when the
record had an exact 125 Hz channel, at least 60,001 samples, a supported uniform
WFDB encoding, and no invalid sentinel in the window. The first 20 eligible
subjects were retained. No waveform was selected or excluded by visual
inspection or detector output. These 20 subjects and their raw-window hashes
are distinct from the curated cohort and total approximately 160 minutes.

The annotations were not used to construct objects or tune individual
boundaries. They were consulted after construction as an external diagnostic.
The frozen LLM-selected detector was likewise treated as a comparison path,
not as ground truth. The object-level results therefore measure agreement
among explicit constructions and annotations rather than clinical detection
accuracy.

## 5. Methods

### 5.1 Development-versus-transfer protocol

The study uses phase labels that constrain the claims that can be made from
each result.

| Phase | Records | Permitted activity | Evidential status |
| --- | --- | --- | --- |
| Exploratory development | Subject 1 | Inspect waveform; choose and revise contracts; harmonize measures; debug boundaries | Generates hypotheses and implementation; no transfer claim |
| Initial frozen transfer | Subjects 2–53 | Run the locked comparator and absolute FeatureGraph rule; no per-subject tuning | Evidence about the initial representation; retained as an ablation |
| Final-representation development | Subjects 1–53 | Test envelope boundaries and exact-plateau intervals after inspecting failures | Developmental evidence for the final representation |
| Prospective confirmation | First 20 eligible non-BIDMC MIMIC-II subjects | Freeze selection, construction, comparator, matching, and four directional criteria before opening outputs | Prospective transfer evidence for the interval-to-point correction |

The absolute FeatureGraph rule and frozen SciPy comparator were locked after
subject 1. The MAD and hysteresis variants were conceived after initial
transfer failures and remain diagnostic ablations. The envelope and plateau
rules were developed after examining the 53 BIDMC records, including severe
failures on subjects 5, 35, 38, and 39. Their BIDMC results are consequently
post hoc even though one fixed rule was applied to every record.

Before the MIMIC-II confirmation outputs were examined, the repository fixed
the subject-selection algorithm, exclusion rules, source window, envelope,
plateau projection, comparator, matching tolerance, and four success criteria:
preserve detected peak count in every window, do not reduce cohort matches, do
not increase comparator-only objects, and reduce median absolute peak error.
This separation prevents three invalid substitutions: development improvement
is not prospective transfer, comparator agreement is not clinical accuracy,
and a bounded candidate episode is not automatically a breath.

### 5.2 Final FeatureGraph object representation

Let `x_t` be the raw respiration value at sample `t`. FeatureGraph retains
`x_t` unchanged for measurement and builds a separate construction signal by
applying a 100-sample rolling maximum followed by a 100-sample rolling mean.
For the offline study the result is shifted backward by 100 samples; invalid
endpoint rows are excluded and windows are never joined across subjects.
Rising is a positive one-sample difference of this aligned envelope. Entry to
rising creates a candidate trough transition and exit creates a candidate peak
transition.

Transition times are not forced to stand in for extrema. Every exact
constant-valued run containing an already detected peak or trough is stored as
an interval `[l,r]`. Its deterministic point projection is

$$
l + \left\lfloor\frac{r-l}{2}\right\rfloor.
$$

The original transition anchor and both interval edges remain available. A
complete object requires a strictly ordered trough interval, peak interval,
and subsequent trough interval. If midpoint projections overlap or violate
that order, the object is retained with
`plateau_boundary_ambiguous=True` and excluded from complete-object metrics.
Endpoint fragments likewise remain represented with `is_complete=False`.

This construction does not assert that the waveform is physiologically
oscillatory or that every object is a breath. It states how observed changes
become bounded candidate objects while preserving uncertainty that point-only
output would conceal.

### 5.3 Frozen SciPy comparator and its provenance

A context-isolated LLM received only the subject 1 waveform, its 125 Hz
sampling rate, a required object schema, and a measurement contract. It selected
a fourth-order 0.8 Hz Butterworth low-pass filter with zero-phase application,
`scipy.signal.find_peaks` on the filtered signal and its negation, a minimum
distance of 188 samples, prominence 0.08, and cycles defined by consecutive
troughs containing exactly one peak.

The method, parameters, endpoint rules, and returned object table were saved
and reproduced as conventional deterministic Python. SciPy therefore remains
a dependency of the comparator path, including its distance, prominence, and
flat-peak behavior; it is not a FeatureGraph dependency or implementation of
the FeatureGraph construction. The comparator is an independently specified
point detector, not respiratory ground truth.

Exact model/session metadata for the proposal interaction were not retained.
The reproducible artifact is the frozen method and its outputs, not the
original model's decision to propose it.

### 5.4 Measurement contracts

For a complete object with start `b`, peak `p`, and end `e`:

- period is the distance between consecutive peak indices divided by 125;
- full excursion is the raw within-object maximum minus minimum;
- FeatureGraph radius amplitude is half the full excursion; and
- temporal symmetry is

$$
1 - \frac{|(p-b)-(e-p)|}{e-b},
$$

which is bounded in `[0,1]`.

The first corrected notebook comparison had reported FeatureGraph radius
amplitude against the LLM's full excursion and a historical symmetry value
using an incompatible definition. These values were not treated as
disagreements after the contracts were identified. The object-level
comparison uses the harmonized full-excursion and bounded-symmetry formulas.

### 5.5 Object and annotation matching

Complete FeatureGraph and LLM objects were sorted by peak index and matched
one-to-one in temporal order within 63 samples (approximately 0.5 seconds).
The dynamic-programming matcher maximizes the number of ordered matches and
then minimizes total absolute peak error. Unmatched objects are retained in
separate audit tables.

Candidate peaks from each detector were independently matched to both BIDMC
annotation series under the same tolerance. Each detected and annotated peak
could be used at most once. Annotation agreement was summarized in both
directions: the fraction of detected peaks matched and the fraction of
annotated peaks recovered.

### 5.6 Development ablation: frozen absolute threshold

The initial FeatureGraph construction computed

$$
d_t = x_t - x_{t-45}
$$

and defined rising as $R_t = \mathbf{1}(d_t > 0.15)$. Internally bounded
non-rising gaps of at most seven samples were closed. Rising entries created
candidate troughs and exits created candidate peaks. This subject-1 rule was
applied unchanged to all 53 subjects, with no subject-specific parameters or
manual boundary corrections. It is retained to show why the final envelope
and interval representation was needed; it is not the current construction.

### 5.7 MAD-normalized cohort

The second experiment tested whether subject-level waveform scale explained
the transfer failures. For each subject,

$$
s = \mathrm{median}(|d_t - \mathrm{median}(d)|)
$$

and

$$
z_t = d_t / s.
$$

Subject 1 supplied the only calibration:

$$
k = 0.15 / s_1 = 0.807624.
$$

The rising state for every subject was then `z_t > k`. All other boundary,
gap, completeness, measurement, matching, and annotation rules remained
unchanged. Raw respiration values were preserved and used for amplitude and
full-excursion measurements.

The MAD experiment was an ablation of scale normalization, not a new tuning
exercise. Hysteresis was excluded so that only the normalization changed.
When MAD equaled zero, the construction was declared undefined; no arbitrary
fallback scale was substituted.

### 5.8 Prospective confirmation protocol

The confirmation compared two projections of the same frozen envelope events:
the transition-derived leading edge and the midpoint of the exact extremum
interval. Both variants used identical samples and detected event identities;
raw within-object extrema remained the source of full excursion. This isolates
representation of an extended extremum from detection of the event itself.

The SciPy comparator, 63-sample one-to-one matching tolerance, and object
metrics were frozen unchanged. Selection scanned non-BIDMC MIMIC-II source
subjects deterministically until 20 eligible windows were obtained. One
otherwise eligible candidate was rejected for invalid WFDB samples under the
predeclared validity rule; a selected subject producing zero objects under both
methods remained in the cohort. The protocol and runner hashes were recorded
before the output tables were interpreted.

For a causal implementation, the detection time is distinct from the
offline-aligned event time: a plateau midpoint becomes known only after the
upper edge of the interval, and the trailing rolling windows impose additional
latency. FeatureGraph retains these timestamps separately rather than treating
offline centering as a real-time detector.

## 6. Results

### 6.1 Final plateau-aware representation on 53 BIDMC records

The final construction detected 8,205 peak events across all 53 subjects and
produced 8,133 complete FeatureGraph objects. Of 7,168 complete comparator
objects, 7,086 matched; 1,047 FeatureGraph-only and 82 comparator-only objects
remained.

| Measure, all 53 subjects | Envelope leading edge | Plateau midpoint |
| --- | ---: | ---: |
| Detected FeatureGraph peak events | 8,205 | 8,205 |
| Complete FeatureGraph objects | 8,180 | 8,133 |
| Complete comparator objects | 7,168 | 7,168 |
| Matched objects | 6,513 | 7,086 |
| FeatureGraph-only objects | 1,667 | 1,047 |
| Comparator-only objects | 655 | 82 |
| Median subject FeatureGraph matched fraction | 88.80% | 94.44% |
| Median subject comparator matched fraction | 100% | 100% |
| Median absolute peak error | 16 samples | 6.5 samples |
| 90th-percentile absolute peak error | 45 samples | 24 samples |
| Median absolute period error | 0.080 s | 0.056 s |
| Median absolute full-excursion error | 0 | 0 |
| Median absolute temporal-symmetry error | 0.0943 | 0.0967 |

Midpoint projection did not add or delete a detected event. It changed how an
extended extremum was represented and how neighboring intervals composed into
complete objects. Forty-seven formerly complete candidates became explicitly
boundary-ambiguous; the saved ambiguity table has 100 rows, including 53
already-partial endpoint fragments. Matches increased on 21 subjects, were
unchanged on 31, and decreased by one on subject 36.

Agreement with both BIDMC annotation series also improved. FeatureGraph peaks
matched to annotator 1 increased from 76.03% to 85.36%, and annotated peaks
recovered increased from 85.59% to 96.10%. Corresponding annotator-2 values
increased from 79.74% to 88.62% and from 88.65% to 98.51%. These are agreement
rates, not clinical sensitivity or positive predictive value.

Plateau-shaped subjects changed most: baseline matches increased from 22 to
119 on subject 35, from 44 to 125 on subject 38, and from zero to 52 on subject
39. Their median post-projection peak errors were 1, 7, and 7.5 samples.
Subject 5 increased from 30 to 74 matches but retained 89 unmatched complete
FeatureGraph objects, showing that interval projection does not resolve every
source of detector disagreement.

### 6.2 Prospective confirmation on 20 untouched source subjects

The deterministic archive scan considered 124 non-BIDMC source-subject
directories before obtaining 20 eligible subjects. The selected windows had 20
distinct raw-data hashes and contained approximately 160 minutes of RESP. One
selected subject produced no object under either construction and was retained.

All four predeclared criteria passed.

| Measure | Envelope leading edge | Plateau midpoint | Delta |
| --- | ---: | ---: | ---: |
| Detected FeatureGraph peak events | 3,811 | 3,811 | 0 |
| Complete FeatureGraph objects | 3,802 | 3,773 | -29 |
| Complete comparator objects | 2,941 | 2,941 | 0 |
| Matched objects | 2,792 | 2,859 | +67 |
| FeatureGraph-only objects | 1,010 | 914 | -96 |
| Comparator-only objects | 149 | 82 | -67 |
| Aggregate FeatureGraph matched fraction | 73.4% | 75.8% | +2.4 points |
| Aggregate comparator matched fraction | 94.9% | 97.2% | +2.3 points |
| Median absolute peak error | 17 samples | 7 samples | -10 samples |
| 90th-percentile absolute peak error | 50 samples | 24 samples | -26 samples |
| Median absolute period error | 0.088 s | 0.056 s | -0.032 s |
| Median absolute full-excursion error | 0 | 0 | 0 |
| Median absolute temporal-symmetry error | 0.0922 | 0.0531 | -0.0391 |

Matches increased on 13 subjects and were unchanged on seven; none decreased.
Comparator-only counts decreased on the same 13 subjects. FeatureGraph-only
counts decreased on 18 subjects and were unchanged on two. Among the 19
subjects with matched peaks, median peak error decreased on 16 and was
unchanged on three. Forty-eight ambiguous objects were represented explicitly,
causing 29 formerly complete objects to be excluded rather than silently
forced into strict point order.

The prospective result confirms transfer of the interval-to-point
representation correction. It does not establish detector equivalence: 914
FeatureGraph-only and 82 comparator-only complete objects remain. The source
windows also lack independent manual breath annotations, so this experiment
does not establish the physiological meaning of those candidates.

### 6.3 Localization of detector-discordant candidate episodes

The 1,047 BIDMC FeatureGraph-only complete objects are strongly concentrated
rather than spread uniformly among records. Seven subjects (5, 13, 14, 19,
27, 33, and 39) account for 555 objects, or 53.0%; the ten highest-count
subjects account for 678, or 64.8%. Six subjects have none, and 23 have five or
fewer. The descriptive Gini coefficient of per-subject counts is 0.64.

| Subject | FeatureGraph-only objects | Share of total |
| ---: | ---: | ---: |
| 13 | 136 | 13.0% |
| 19 | 92 | 8.8% |
| 5 | 89 | 8.5% |
| 14 | 63 | 6.0% |
| 33 | 61 | 5.8% |
| 39 | 60 | 5.7% |
| 27 | 54 | 5.2% |

The objects are not concentrated at one normalized position across the cohort:
counts in successive tenths of the records range from 79 to 127. Within some
subjects they form local bursts; subject 25 has 30 of 32 unmatched objects in
one tenth of its record, while subjects 13, 33, and 39 distribute them across
many regions. Of all 1,047 episodes, 680 are excluded by both annotation series
and 367 are not; none of subject 39's 60 is jointly excluded.

FeatureGraph therefore labels and passes these rows forward as
*detector-discordant candidate episodes*. The label identifies a localized
computational disagreement. It is deliberately not a diagnosis, a claim of
abnormal breathing, or a declaration that either detector is correct.

### 6.4 Development and ablation history

The following experiments explain how the final representation was reached.
They are retained for transparency but are not the paper's primary result.

#### 6.4.1 Development-record agreement

On subject 1, native FeatureGraph produced 174 complete objects and the
blinded LLM path produced 169. All 169 LLM objects matched FeatureGraph
objects; FeatureGraph had five unmatched complete candidates and the LLM had
none. Median absolute peak error was 10 samples (0.080 seconds), with a maximum
of 29 samples (0.232 seconds).

| Matched-object measure | FeatureGraph | LLM path | Agreement |
| --- | ---: | ---: | --- |
| Complete objects | 174 | 169 | 169 matched; 5 FeatureGraph-only |
| Mean period | 2.802 s | 2.821 s | Median absolute error 0.040 s |
| Mean full excursion | 0.896 | 0.903 | Median absolute error 0.00489 |
| Mean temporal symmetry | 0.596 | 0.844 | Median absolute error 0.250 |

The result supports genuine agreement on the principal repeated objects,
period, and excursion. Symmetry does not agree comparably because the
transition rule and filtered local-extrema rule place trough boundaries
differently. This is a boundary-semantics mismatch, not an arithmetic or unit
mismatch.

#### 6.4.2 Original absolute-threshold transfer

Across all 53 subjects, the native absolute rule produced 8,960 complete
objects and the frozen LLM path produced 7,168. Of these, 6,200 matched.

| Absolute construction, subjects 1–53 | Result |
| --- | ---: |
| FeatureGraph complete objects | 8,960 |
| LLM-baseline complete objects | 7,168 |
| Matched objects | 6,200 |
| FeatureGraph-only objects | 2,760 |
| Baseline-only objects | 968 |
| FeatureGraph matched fraction | 69.2% |
| Baseline matched fraction | 86.5% |

On the frozen subjects 2–53, FeatureGraph produced 8,786 objects, the
baseline produced 6,999, and 6,031 matched. Median subject-level matched
fractions were 78.5% of FeatureGraph objects and 99.1% of baseline objects.
Peak placement for matched objects remained close (median absolute difference
12 samples), but transfer was uneven. Some records were heavily
over-segmented, while subjects including 5, 13, 19, 27, and 45 were severely
under-detected. Thus the absolute threshold did not fail in one uniform way.

#### 6.4.3 MAD normalization versus the original run

MAD normalization was defined for 51 of 53 records. Subjects 35 and 39 had
zero 45-sample difference MAD and were excluded from MAD aggregates. The
original absolute construction remained defined for both; it produced 144
versus 121 baseline objects on subject 35 and 115 versus 54 on subject 39.

The table below compares both constructions on the same 51 valid records.

| Measure, same 51 subjects | Absolute | MAD normalized |
| --- | ---: | ---: |
| FeatureGraph complete objects | 8,701 | 12,403 |
| LLM-baseline complete objects | 6,993 | 6,993 |
| Matched objects | 6,030 | 6,850 |
| FeatureGraph-only objects | 2,671 | 5,553 |
| Baseline-only objects | 963 | 143 |
| FeatureGraph objects matched | 69.3% | 55.2% |
| Baseline objects matched | 86.2% | 98.0% |
| Median subject absolute count error | 33 | 67 |
| Subjects over baseline count | 44 | 51 |
| Subjects under baseline count | 7 | 0 |
| Median absolute peak error | 12 samples | 13 samples |
| Median absolute period error | 0.080 s | 0.168 s |
| Median absolute full-excursion error | 0.0000 | 0.0020 |
| Median absolute symmetry error | 0.347 | 0.274 |

MAD normalization recovered more of the baseline on 27 subjects and never
reduced the number of matched baseline objects. This was particularly visible
in several original under-detection cases: subject 13 increased from 9 to 105
matched objects, subject 19 from 12 to 121, subject 27 from 7 to 86, and
subject 45 from 3 to 127. However, the total candidate counts on these records
became 518, 421, 561, and 237, respectively. Only 11 subjects moved closer to
the baseline count; 37 moved farther away, with three unchanged.

Annotation comparisons show the same recall–precision tradeoff. On the common
51 records, the fraction of annotated peaks recovered increased from 83.3% to
95.6% for annotator 1 and from 84.5% to 97.7% for annotator 2. The fraction of
FeatureGraph detections matched to annotations fell from 67.1% to 54.0% and
from 68.9% to 56.0%, respectively.

MAD normalization therefore addressed one real weakness, scale-dependent
under-detection, but did not produce a transferable peak-selection rule. It
converted a mixed failure pattern into systematic over-segmentation, worsened
period agreement, and was mathematically undefined on two quantized records.

![Complete object counts by subject](subject_object_counts.png)

**Figure 1.** Complete candidate-object counts for the frozen LLM-selected
baseline, the original FeatureGraph absolute threshold, and MAD-normalized
FeatureGraph. Missing MAD values at subjects 35 and 39 denote undefined zero
difference scales, not zero detected objects.

#### 6.4.4 Hysteresis diagnostic

An exploratory subject 5 ablation retained the MAD-normalized entry threshold
and lowered the exit threshold from `1.0k` through `0.0k`. Complete candidates
fell only from 388 to 365, while annotation match counts did not improve. This
indicates that most extra candidates result from repeated threshold re-entry,
not brief flicker within a neutral band. Because this diagnostic did not solve
the transfer problem, hysteresis was not included in the full MAD cohort.

## 7. Capability and dependency ledger

| Capability | Source during development | Preserved without live LLM access? |
| --- | --- | --- |
| Propose filtering and peak detector | LLM | The chosen method is preserved; proposing a new one is not |
| Select domain-relevant peaks | Researcher/LLM judgment | Only as frozen explicit rules; not inferred by FeatureGraph |
| Execute LLM-selected baseline | NumPy, pandas, SciPy | Yes |
| Construct rising/falling states | FeatureGraph from researcher parameters | Yes |
| Expose trough/peak events and wave IDs | FeatureGraph | Yes |
| Retain extremum intervals, transition anchors, and midpoint projections | FeatureGraph representation | Yes |
| Distinguish offline event time from causal detection time | FeatureGraph representation | Yes |
| Flag overlapping or degenerate extremum intervals | FeatureGraph representation | Yes |
| Retain incomplete endpoint objects | FeatureGraph | Yes |
| Summarize period, excursion, symmetry | Frozen measurement contracts | Yes |
| Match and audit individual objects | Deterministic comparison code | Yes |
| Diagnose transfer failures across subjects | Saved object and annotation tables | Yes |
| Localize detector-discordant candidate episodes and bursts | Saved bounded object tables | Yes |
| Invent a transferable detector automatically | Not achieved | No |
| Establish clinical validity | Requires domain expertise and clinical protocol | No |

The preserved functionality is substantial. Both frozen paths can run without
an LLM, produce object tables, expose disagreements, and support continued
maintenance by a human researcher. The study also clarifies what was not
replaced: the judgment required to decide which observed transitions should
count as meaningful objects in a new record or domain.

## 8. Discussion

The principal result is that temporal representation, not only event
detection, determined whether the methods appeared to agree. A transition out
of rising, an exact flat maximum, and the midpoint convention of a point
detector can refer to the same observed event while producing different sample
indices. FeatureGraph can retain all three without changing event identity.
That separation preserved 8,205 BIDMC peak events while adding interval edges,
improving alignment, and exposing 47 otherwise hidden boundary ambiguities.

The prospective MIMIC-II run changes this from a purely post hoc explanation
to transfer evidence for a specific representation correction. The midpoint
projection passed every predeclared directional criterion, improved or
preserved matches on every subject, and reduced peak, period, and symmetry
errors on untouched source windows. Because leading-edge and midpoint variants
shared the same detected events, the result cannot be attributed to adding a
more permissive detector. It supports the narrower claim that an extended
extremum is better represented as an interval and projected only when a
point-based comparison requires one.

The remaining 1,047 FeatureGraph-only complete objects prevent a general
equivalence claim, but their localization is itself an achieved capability.
The unmatched set is concentrated in a limited group of subjects and contains
both isolated objects and temporally contiguous bursts. FeatureGraph preserves
the subject, boundaries, component extrema, measurements, neighborhood, and
annotation agreement of each episode even when the current representation
cannot classify its morphology. This converts aggregate transfer failure into
an inspectable object set that can support later signal-quality analysis,
domain review, or comparison with clinical events.

The localization result changes the interpretation of residual disagreement.
The data are short recordings from critically ill patients, so heterogeneous
respiratory morphology, physiological irregularity, and measurement artifact
are all plausible sources of detector disagreement. The present study cannot
distinguish among them. It can show where the expected cycle representation
becomes unstable and whether that instability is persistent, isolated, or
bursty. Interval projection improves compatibility with point-based
evaluators; it does not determine which candidate cycles are physiologically
meaningful. Likewise, unchanged full-excursion agreement and slightly worse
symmetry agreement show that correcting peak projection does not harmonize
every boundary-sensitive property.

The earlier absolute-threshold, MAD, and hysteresis experiments remain useful
because they distinguish representation from detector tuning. The absolute
rule transferred unevenly; MAD recovered more comparator events but caused
systematic over-segmentation; hysteresis did not repair the subject-5 pattern.
Those failures motivated the final construction, but they are not the current
FeatureGraph claim. The current claim is that declared temporal semantics can
be executed, transferred, inspected, and revised at object level.

The LLM origin provides an additional preservation result. The comparator
method and its object schema now execute without a live model, while the
FeatureGraph path exposes assumptions that were implicit in the point-detector
workflow. This is secondary to the representation result but demonstrates that
an LLM-originated analysis can become a durable computational artifact rather
than remain dependent on a conversation.

## 9. Threats to validity

### 9.1 Construct validity

The primary construct is *explicit temporal representation*, operationalized
as the ability to rerun declared construction and measurement contracts,
retain distinct event and interval semantics, inspect object boundaries, and
reproduce saved tables. Agreement with the frozen SciPy path is not respiratory
ground truth. The two manual annotation series provide an external diagnostic,
but annotators differ and may encode peak semantics that differ from either
constructed object type. Preservation of an LLM-originated analysis is a
secondary construct and does not imply preservation of latent model reasoning.

Period and full excursion have harmonized contracts; trough-sensitive symmetry
does not have equivalent boundary semantics across detectors. Reporting that
quantity alongside period risks overstating disagreement in the summarized
object itself. We therefore interpret symmetry as a boundary-semantic
diagnostic, not a validated physiological property. Likewise, accumulation is
area over a normalized waveform baseline and cannot be interpreted as
calibrated respiratory volume.

### 9.2 Internal validity

Subject 1 was inspected repeatedly while parameters, endpoint rules, and
measurement contracts were developed. Its agreement statistics are therefore
development results and are vulnerable to researcher degrees of freedom. The
absolute transfer pass reduces this threat by locking both paths before
subjects 2–53 and prohibiting per-subject correction. The matching tolerance
and dynamic-programming objective were also declared in code, but alternative
tolerances or matching objectives could change unmatched counts; saved audit
tables make that sensitivity testable.

The MAD construction was proposed after observing absolute-rule failures, and
the subject 5 hysteresis test followed inspection of a specific failure. The
rolling envelope and plateau midpoint were likewise developed after inspecting
subject 1 and cohort failures, so their 53-record results are post hoc. The
20-subject confirmation reduces this threat because the representation,
selection algorithm, matching, and directional criteria were frozen before
outputs were examined. It does not erase prior exposure to the broader
MIMIC-II/BIDMC source domain or constitute random population sampling.

### 9.3 External validity

BIDMC contains 53 short recordings from critically ill patients, all sampled
at 125 Hz and distributed through one dataset. The confirmation adds 20
non-BIDMC MIMIC-II source subjects but retains the same archive family,
sampling rate, and short-window design. Its windows lack independent manual
breath annotations. Results may not generalize to other sensors, sampling
rates, preprocessing conventions, populations, or longer recordings. The
researcher lacked respiration-domain expertise, which precludes clinical or
physiological claims. Independent data and domain review are required before
using these objects as breath measurements.

For the same reason, a detector-discordant candidate episode must not be interpreted as
an abnormal breath. It may reflect physiological morphology, sensor artifact,
annotation convention, baseline suppression, FeatureGraph over-segmentation,
or some combination of these mechanisms. The current contribution is exact
localization and preservation of the disagreement, not determination of its
clinical cause.

The study evaluates one LLM-proposed SciPy method and one FeatureGraph
representation. It does not estimate variation across models, prompts,
sessions, or human implementers. The original exploratory chat is unavailable,
and the context-isolated proposal session lacks exact model/session metadata.
Consequently, the frozen method is reproducible, while the act of proposing it
is not.

### 9.4 Conclusion and statistical validity

The object counts are a census of the selected BIDMC records rather than a
sample used for population inference; no clinical confidence intervals or
hypothesis tests are claimed. Aggregate agreement can conceal offsetting
errors, so the study reports one-to-one matches, unmatched objects, per-subject
counts, boundary errors, and annotation agreement in both directions. The MAD
comparison is restricted to the same 51 valid records; subjects 35 and 39 are
reported separately rather than silently dropped.

The frozen baseline is a comparator, not a gold standard. Terms such as
"recall" and "precision" are avoided for baseline matching unless the
denominator is stated, and annotation matches are described as agreement rather
than clinical sensitivity or positive predictive value.

### 9.5 Reproducibility and provenance validity

The repository preserves prompts, raw inputs, returned object tables, a written
method, deterministic reproduction code, construction parameters, tests, and
generated comparisons. This supports computational reproduction of the frozen
method and all reported tables. It does not recover the undocumented original
conversation or prove that another model would choose the same analysis.
Software and data services may also change; the tagged release, Zenodo archive,
checksums, and environment records reduce but do not eliminate that risk.

Finally, computational cost savings are not yet quantified. Deterministic
execution is expected to be cheaper and more stable than repeated LLM analysis,
but a defensible comparison requires fixed tasks, recorded runtimes, hardware,
model usage, and contemporaneous pricing or energy measurements.

## 10. AI-use disclosure

AI use occurred in three distinct roles and is reported separately so that an
undocumented conversation is not conflated with a reproducible method.

1. **Original exploratory interaction.** An earlier LLM conversation helped
   propose and interpret the initial respiration analysis. That conversation
   was not retained. Its transcript, exact model identifier, system configuration, and
   sampling settings are unavailable. It is historical motivation only and is
   not treated as reproducible evidence.
2. **Context-isolated frozen proposal.** A later LLM session received the
   archived subject 1 waveform, sampling rate, object schema, and frozen prompt,
   without FeatureGraph outputs. Its returned object table and written SciPy
   method were archived. The selected
   method was translated into deterministic Python, and its saved outputs are
   reproduced and tested without an LLM. In this paper, *reproducible frozen
   method* refers to that code-level reproduction, not regeneration of the
   original LLM response.
3. **Research and writing assistance.** LLM tools assisted with code debugging and testing, experiment orchestration, literature discovery, editorial feedback, formatting, and consistency checking. The author formulated the research question and conceptual framework, made the study-design decisions, selected and approved the construction and measurement contracts and parameters, executed and inspected the analyses, wrote and revised the manuscript’s substantive narrative, verified the reported claims against saved artifacts, determined the interpretation of the results, and accepts responsibility for all claims and conclusions.

AI-generated suggestions were not accepted as evidence merely because they
were produced by a model. Numerical claims are tied to versioned scripts and
tables; literature claims are tied to cited sources; and known gaps in AI
provenance remain disclosed rather than reconstructed retrospectively. The
full experiment-level disclosure is maintained in
`experiments/bidmc_llm_capture/AI_USE_DISCLOSURE.md`.

## 11. Conclusion

FeatureGraph represented candidate respiration cycles as explicit temporal
objects whose transition anchors, extremum intervals, point projections,
completeness, ambiguity, and measurements remain separately inspectable. On 53
BIDMC records, the final plateau-aware representation preserved all detected
events while aligning 7,086 of 7,168 comparator objects. On 20 prospectively
selected untouched source subjects, the same interval-to-point correction
passed all four predeclared transfer criteria and reduced median matched-peak
error from 17 to 7 samples.

The result is not detector equivalence or clinical validation. Residual
FeatureGraph-only objects remain, are concentrated in a minority of records,
and may reflect physiological morphology, measurement artifact, annotation
convention, or over-segmentation. The appropriate FeatureGraph behavior is to
label and preserve those detector-discordant candidate episodes for downstream
review, not to infer their meaning.

The study therefore supports FeatureGraph's present purpose: turning implicit
sample-level analytical decisions into durable, executable, object-level
representations. The frozen LLM-originated comparator demonstrates analytical
preservation, but the broader contribution is the ability to distinguish what
was observed, how it was bounded, how it was projected, and what remains
uncertain.

## 12. Reproducibility

The beta release stores the blinded prompt, comparator method record, raw and
object tables, frozen reproduction code, subject-level comparisons,
unmatched-object audits, annotation comparisons, development ablations,
plateau intervals, and explicit boundary-ambiguity rows. The live study
repository additionally stores the prospective confirmation protocol,
selection audit, hashes, decision record, and object-level outputs.

### 12.1 Code and data availability

The exact computational artifact used for this study is FeatureGraph
version 0.1.0b1, archived on Zenodo at
[https://doi.org/10.5281/zenodo.21984186](https://doi.org/10.5281/zenodo.21984186)
and released from Git commit
[`e6df4d0a309bffdf36c4f2e3dbcf3ee29f9f9c4b`](https://github.com/featuregraph/featuregraph/tree/e6df4d0a309bffdf36c4f2e3dbcf3ee29f9f9c4b).
The public release includes the frozen comparator, FeatureGraph constructions,
tests, subject-level summaries, object-level audit tables, and verification
manifest. The source recordings and manual breath annotations are available
from the BIDMC PPG and Respiration Dataset, version 1.0.0, under its PhysioNet
terms at [https://doi.org/10.13026/C2208R](https://doi.org/10.13026/C2208R).

```bash
PYTHONPATH=. python experiments/bidmc_llm_capture/multi_subject_comparison.py \
  --subjects 1-53 --jobs 4 --scaling absolute \
  --output-directory experiments/bidmc_llm_capture/results/multi_subject

PYTHONPATH=. python experiments/bidmc_llm_capture/multi_subject_comparison.py \
  --subjects 1-53 --jobs 4 --scaling mad \
  --output-directory experiments/bidmc_llm_capture/results/mad_multi_subject

PYTHONPATH=. python \
  experiments/bidmc_llm_capture/compare_scaling_runs.py

PYTHONPATH=src:. python \
  experiments/bidmc_llm_capture/multi_subject_comparison.py \
  --subjects 1-53 --jobs 4 --construction envelope_plateau \
  --output-directory \
    experiments/bidmc_llm_capture/results/envelope_plateau_multi_subject

PYTHONPATH=src:. python \
  experiments/mimic2_envelope_confirmation/run_confirmation.py \
  --output-directory results/mimic2_envelope_confirmation
```

## References

1. Pimentel, M. A. F., Johnson, A. E. W., Charlton, P. H., and Clifton,
   D. A. *BIDMC PPG and Respiration Dataset*, version 1.0.0. PhysioNet,
   2018. [https://doi.org/10.13026/C2208R](https://doi.org/10.13026/C2208R).
2. Pimentel, M. A. F., Johnson, A. E. W., Charlton, P. H., Birrenkott, D.,
   Watkinson, P. J., Tarassenko, L., and Clifton, D. A. “Toward a Robust
   Estimation of Respiratory Rate From Pulse Oximeters.” *IEEE Transactions
   on Biomedical Engineering* 64(8), 1914–1923, 2017.
   [https://doi.org/10.1109/TBME.2016.2613124](https://doi.org/10.1109/TBME.2016.2613124).
3. Virtanen, P. et al. “SciPy 1.0: Fundamental Algorithms for Scientific
   Computing in Python.” *Nature Methods* 17, 261–272, 2020.
   [https://doi.org/10.1038/s41592-019-0686-2](https://doi.org/10.1038/s41592-019-0686-2).
4. Habib, N. *FeatureGraph*, version 0.1.0b1, 2026.
   [https://doi.org/10.5281/zenodo.21984186](https://doi.org/10.5281/zenodo.21984186).
5. Peng, R. D. “Reproducible Research in Computational Science.” *Science*
   334(6060), 1226–1227, 2011.
   [https://doi.org/10.1126/science.1213847](https://doi.org/10.1126/science.1213847).
6. Sandve, G. K., Nekrutenko, A., Taylor, J., and Hovig, E. “Ten Simple
   Rules for Reproducible Computational Research.” *PLOS Computational
   Biology* 9(10), e1003285, 2013.
   [https://doi.org/10.1371/journal.pcbi.1003285](https://doi.org/10.1371/journal.pcbi.1003285).
7. Wilkinson, M. D. et al. “The FAIR Guiding Principles for Scientific Data
   Management and Stewardship.” *Scientific Data* 3, 160018, 2016.
   [https://doi.org/10.1038/sdata.2016.18](https://doi.org/10.1038/sdata.2016.18).
8. Di Tommaso, P. et al. “Nextflow Enables Reproducible Computational
   Workflows.” *Nature Biotechnology* 35, 316–319, 2017.
   [https://doi.org/10.1038/nbt.3820](https://doi.org/10.1038/nbt.3820).
9. Murta, L., Braganholo, V., Chirigati, F., Koop, D., and Freire, J.
   “noWorkflow: Capturing and Analyzing Provenance of Scripts.” In
   *Provenance and Annotation of Data and Processes*, 71–83, 2014.
   [https://doi.org/10.1007/978-3-319-16462-5_6](https://doi.org/10.1007/978-3-319-16462-5_6).
10. Dibia, V. “LIDA: A Tool for Automatic Generation of Grammar-Agnostic
    Visualizations and Infographics Using Large Language Models.” In
    *Proceedings of ACL 2023: System Demonstrations*, 113–126, 2023.
    [https://doi.org/10.18653/v1/2023.acl-demo.11](https://doi.org/10.18653/v1/2023.acl-demo.11).
11. Xie, L., Zheng, C., Xia, H., Qu, H., and Zhu-Tian, C. “WaitGPT:
    Monitoring and Steering Conversational LLM Agent in Data Analysis with
    On-the-Fly Code Visualization.” In *UIST 2024*, 2024.
    [https://doi.org/10.1145/3654777.3676374](https://doi.org/10.1145/3654777.3676374).
12. Chollet, F. “On the Measure of Intelligence.” arXiv:1911.01547, 2019.
    [https://doi.org/10.48550/arXiv.1911.01547](https://doi.org/10.48550/arXiv.1911.01547).
13. Lin, J., Keogh, E., Wei, L., and Lonardi, S. “Experiencing SAX: A Novel
    Symbolic Representation of Time Series.” *Data Mining and Knowledge
    Discovery* 15, 107–144, 2007.
    [https://doi.org/10.1007/s10618-007-0064-z](https://doi.org/10.1007/s10618-007-0064-z).
14. Ye, L. and Keogh, E. “Time Series Shapelets: A New Primitive for Data
    Mining.” In *KDD 2009*, 947–956, 2009.
    [https://doi.org/10.1145/1557019.1557122](https://doi.org/10.1145/1557019.1557122).
