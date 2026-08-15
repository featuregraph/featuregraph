# From LLM-Proposed Analysis to Maintainable Behavioral Objects: A BIDMC Respiration Case Study

**Nazia Habib**  
Draft research record, August 2026

## Abstract

Large language models (LLMs) can propose useful data analyses, but an LLM
interaction is not itself a durable computational representation. We study a
practical question: if LLM access disappeared, how much of an LLM-proposed
time-series analysis could a researcher continue to run, inspect, validate,
and maintain? A context-isolated LLM received one raw respiration record from
the BIDMC PPG and Respiration Dataset and produced a documented SciPy pipeline
and an object table of trough–peak–trough cycles. The researcher then encoded
an independently specified, deterministic transition representation in
FeatureGraph. On the development record, 169 of 169 complete LLM objects
matched FeatureGraph objects within 0.5 seconds; FeatureGraph produced five
additional complete candidates. Typical period and full-excursion
measurements agreed closely, while temporal symmetry remained sensitive to
different trough semantics.

We then froze the construction and evaluated transfer across all 53 BIDMC
records. The original absolute transition rule produced 8,960 complete
FeatureGraph objects and the frozen LLM-selected baseline produced 7,168;
6,200 objects matched, leaving 2,760 FeatureGraph-only and 968 baseline-only
objects. A second experiment normalized the directional difference by a
subject-level median absolute deviation (MAD), retaining a threshold
calibrated only on subject 1. MAD normalization increased baseline coverage on
the 51 records for which it was defined: matched objects increased from 6,030
to 6,850 and baseline-only objects fell from 963 to 143. This apparent recall
gain came with severe over-segmentation: FeatureGraph-only objects increased
from 2,671 to 5,553, and the normalized construction was undefined for two
records with zero difference MAD.

The study demonstrates successful preservation, deterministic execution,
object-level auditability, and explicit failure localization. It does not
demonstrate a generally transferable respiration detector. Determinism
preserved the researcher-specified representation; it did not supply the
missing judgment about which transitions constitute meaningful breaths. This
distinction motivates a transition-only next phase of FeatureGraph and
provides a candid research record of both the achieved capability and its
limits.

## 1. Introduction

LLMs increasingly participate in exploratory analysis by selecting
transformations, proposing algorithms, writing code, and interpreting
results. These capabilities can accelerate research, but they create a
continuity problem. A conversational result may depend on model access,
unstated context, changing model behavior, or code whose conceptual contract
was never separated from its implementation. Re-running code is not the same
as preserving the analysis if the meaning of its intermediate states,
boundaries, exclusions, and measurements remains implicit.

FeatureGraph is a deterministic framework for converting ordered observations
into explicit states, events, and temporally bounded behavioral objects. Its
purpose in this study is not to make FeatureGraph recognize respiration. The
software has no concept of breathing, no learned oscillation classifier, and
no independent knowledge of which peaks should be accepted. A researcher
supplies a transition contract; FeatureGraph applies it exactly, exposes its
sample-level consequences, assigns object identities and completeness, and
calculates documented object properties.

This study asks whether that representation can preserve useful parts of an
LLM-proposed analysis in a form that remains executable and maintainable
without an LLM. It also asks a harder question: whether a construction that
agrees on one record transfers to other subjects. The distinction is
essential. A deterministic system may preserve a rule perfectly while the
rule itself generalizes poorly.

The BIDMC respiration data were selected because they offer 53 public,
eight-minute recordings, a fixed 125 Hz sampling rate, visible repeated
waveform structure, and two independent manual breath-annotation series. The
researcher did not begin with domain expertise in respiratory physiology.
This made the dataset appropriate for studying analytical preservation and
representation, but it also limits the interpretation: this is not a clinical
validation study and no detected quantity is claimed to measure calibrated
airflow or volume.

The contributions are:

1. a reproducible handoff from a raw-data LLM analysis to an explicit,
   deterministic behavioral-object representation;
2. an object-level comparison that distinguishes genuine agreement from
   aggregate cancellation and definition mismatch;
3. a 53-subject transfer evaluation of the original absolute transition rule;
4. a second cohort experiment isolating the effect of subject-level MAD
   normalization; and
5. a capability ledger separating LLM proposal, researcher judgment,
   FeatureGraph execution, conventional signal-processing dependencies, and
   functionality preserved without continued LLM access.

## 2. Data and study scope

The [BIDMC PPG and Respiration Dataset](https://physionet.org/content/bidmc/1.0.0/)
contains 53 recordings extracted from critically ill patients, with
physiological signals sampled at 125 Hz and two sets of manually annotated
breath sample numbers. Each record is approximately eight minutes long. This
study uses the impedance respiration waveform and the two annotation columns.

Subject 1 served as the development record. The initial LLM analysis,
FeatureGraph construction, threshold selection, and object-contract
harmonization were performed on this record. Subjects 2–53 were initially
treated as a frozen transfer cohort. The later MAD experiment reused the
subject-1 calibration and applied one rule to every record; no threshold was
selected separately for an evaluation subject.

The annotations were not used to construct objects or tune individual
boundaries. They were consulted after construction as an external diagnostic.
The frozen LLM-selected detector was likewise treated as a comparison path,
not as ground truth. The object-level results therefore measure agreement
among explicit constructions and annotations rather than clinical detection
accuracy.

## 3. Methods

### 3.1 Blinded raw-data LLM path

A context-isolated LLM received only the subject 1 waveform, its 125 Hz
sampling rate, a required object schema, and a measurement contract. It was
instructed not to use or search for FeatureGraph results. The LLM selected:

1. a fourth-order Butterworth low-pass filter at 0.8 Hz, applied with
   zero-phase forward/backward filtering;
2. `scipy.signal.find_peaks` on the filtered signal and its negation;
3. minimum peak distance of 188 samples and prominence of 0.08; and
4. complete cycles defined as consecutive troughs containing exactly one
   peak.

The LLM returned 169 complete objects and one trailing incomplete fragment.
Its method, libraries, parameters, endpoint rules, and output object table
were saved. A conventional Python function now reproduces this frozen method
without consulting an LLM. SciPy remains a dependency of this comparison path;
its peak-distance and prominence constraints are established signal-processing
operations rather than FeatureGraph behavior.

The exact model/session metadata for the proposal interaction was not retained
in the experiment directory. Consequently, this study claims reproducibility
of the frozen method and outputs, not reproducibility of the original model's
decision to select that method.

### 3.2 FeatureGraph object construction

Let `x_t` be the respiration value at sample `t`. The original native
FeatureGraph construction computes

$$
d_t = x_t - x_{t-45}
$$

and defines the rising state as

$$
R_t = \mathbf{1}(d_t > 0.15).
$$

Internally bounded non-rising gaps of at most seven samples are closed. An
entry into the rising state creates a candidate trough event; an exit creates
a candidate peak event at the preceding sample. Cumulative trough-entry
events assign wave identifiers. A complete object requires a strictly ordered
trough, peak, and subsequent trough and cannot be the final boundary-truncated
wave. Endpoint fragments remain represented with `is_complete=False`.

These rules do not assert that the signal is truly oscillatory or that every
candidate event is a breath. They state exactly how the researcher chose to
partition this waveform into transition-derived objects.

### 3.3 Measurement contracts

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

### 3.4 Object and annotation matching

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

### 3.5 Frozen absolute-threshold cohort

The subject 1 construction—no smoothing, lag 45, threshold 0.15, and maximum
state gap 7—was applied unchanged to all 53 subjects. The frozen LLM-selected
SciPy method was also applied unchanged to all records. No subject-specific
parameters or manual boundary corrections were introduced.

### 3.6 MAD-normalized cohort

The second experiment tested whether subject-level waveform scale explained
the transfer failures. For each subject,

$$
s = \operatorname{median}(|d_t - \operatorname{median}(d)|)
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

## 4. Results

### 4.1 Development-record agreement

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

### 4.2 Original absolute-threshold transfer

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

### 4.3 MAD normalization versus the original run

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

MAD normalization therefore addressed one real weakness—scale-dependent
under-detection—but did not produce a transferable peak-selection rule. It
converted a mixed failure pattern into systematic over-segmentation, worsened
period agreement, and was mathematically undefined on two quantized records.

![Complete object counts by subject](subject_object_counts.png)

**Figure 1.** Complete candidate-object counts for the frozen LLM-selected
baseline, the original FeatureGraph absolute threshold, and MAD-normalized
FeatureGraph. Missing MAD values at subjects 35 and 39 denote undefined zero
difference scales, not zero detected objects.

### 4.4 Hysteresis diagnostic

An exploratory subject 5 ablation retained the MAD-normalized entry threshold
and lowered the exit threshold from `1.0k` through `0.0k`. Complete candidates
fell only from 388 to 365, while annotation match counts did not improve. This
indicates that most extra candidates result from repeated threshold re-entry,
not brief flicker within a neutral band. Because this diagnostic did not solve
the transfer problem, hysteresis was not included in the full MAD cohort.

## 5. Capability and dependency ledger

| Capability | Source during development | Preserved without live LLM access? |
| --- | --- | --- |
| Propose filtering and peak detector | LLM | The chosen method is preserved; proposing a new one is not |
| Select domain-relevant peaks | Researcher/LLM judgment | Only as frozen explicit rules; not inferred by FeatureGraph |
| Execute LLM-selected baseline | NumPy, pandas, SciPy | Yes |
| Construct rising/falling states | FeatureGraph from researcher parameters | Yes |
| Expose trough/peak events and wave IDs | FeatureGraph | Yes |
| Retain incomplete endpoint objects | FeatureGraph | Yes |
| Summarize period, excursion, symmetry | Frozen measurement contracts | Yes |
| Match and audit individual objects | Deterministic comparison code | Yes |
| Diagnose transfer failures across subjects | Saved object and annotation tables | Yes |
| Invent a transferable detector automatically | Not achieved | No |
| Establish clinical validity | Requires domain expertise and clinical protocol | No |

The preserved functionality is substantial. Both frozen paths can run without
an LLM, produce object tables, expose disagreements, and support continued
maintenance by a human researcher. The study also clarifies what was not
replaced: the judgment required to decide which observed transitions should
count as meaningful objects in a new record or domain.

## 6. Discussion

The subject 1 result alone could have supported an overly optimistic claim.
Aggregate counts, rates, periods, and excursions were close, and every LLM
object matched a FeatureGraph object. The cohort experiments reveal why
object-level and multi-subject validation are necessary. A rule can preserve
one analysis faithfully and still fail to transfer.

This does not make the representation unsuccessful. FeatureGraph's role is
separable from detector quality. It deterministically transformed a declared
state rule into inspectable events, identities, complete and incomplete
objects, properties, and audit tables. When the absolute threshold failed,
the failure was visible by subject and object. When MAD normalization shifted
the failure from under-detection to over-segmentation, that tradeoff was
measurable rather than hidden in a narrative summary. When normalization was
undefined, the pipeline rejected the records instead of silently inventing a
scale.

The study therefore supports a narrower but defensible claim: an
LLM-assisted analysis can be converted into a durable computational artifact
whose behavior humans can inspect and maintain after LLM access is lost.
FeatureGraph can preserve the representation and its execution, but it does
not automatically preserve or reproduce all analytical intelligence that led
to the representation.

This distinction also changes the preferred architectural direction. The
current alpha packages the transition rules into an `Oscillation`
construction, even though the software cannot know whether a signal is an
oscillation. A transition-only representation would describe exactly what the
deterministic layer observes: state entries, exits, persistence, boundaries,
and relations among transitions. Higher-order interpretations such as
oscillation or respiration cycle could then be supplied by users or other
systems as compositions over those objects. The failures in this study are
evidence for that separation.

## 7. Limitations

First, the LLM proposal was produced for one development record. Although its
method and outputs are frozen, the missing model/session metadata prevents an
exact replication of the proposal process. Second, the LLM-selected SciPy
path is not ground truth; it is another deterministic detector selected by an
LLM. Manual annotations provide an external check but also differ between
annotators and do not necessarily encode the same peak semantics.

Third, the researcher lacked respiration-domain expertise. This reduced the
risk of silently importing specialist heuristics into the representation, but
it also precludes physiological or clinical claims. The BIDMC signal is
normalized, and accumulation or excursion values must not be interpreted as
calibrated respiratory volume.

Fourth, subject 1 was used for development and threshold calibration. The
absolute cohort results on subjects 2–53 are the primary transfer evidence.
The MAD experiment was motivated after observing the absolute failures and is
therefore a second development-stage ablation, not a preregistered independent
validation. Its negative result should guide a future held-out design rather
than be treated as final detector optimization.

Finally, this study does not yet quantify computational cost savings. Frozen
deterministic execution should be cheaper and more stable than repeated LLM
analysis, but a defensible cost comparison requires recorded runtimes, compute
environments, model pricing or resource use, and a fixed task definition.

## 8. Conclusion

This study began with the question of what would remain if LLM access were
lost. The answer is neither “nothing” nor “the entire analytical capability.”
The LLM-proposed method, researcher-defined representation, deterministic
object construction, measurement contracts, and object-level audits now run
without an LLM. Humans can inspect their states and boundaries, reproduce
their outputs, and identify exactly where they fail.

What did not transfer was the rule for deciding which candidate transitions
should be treated as meaningful breaths. The absolute threshold failed
unevenly across subjects. MAD normalization recovered most baseline objects
but produced severe systematic over-segmentation and failed mathematically on
two records. Hysteresis did not repair the problem. These are not incidental
exceptions to conceal; they are the main scientific result about the boundary
between deterministic preservation and analytical judgment.

The next phase will therefore retain this study as a completed research
record and move FeatureGraph toward transition-only objects. That architecture
better matches what the system can claim: it can represent explicit temporal
changes faithfully, while leaving higher-order semantic interpretation to a
declared human or computational layer.

## Reproducibility

The repository stores the blinded prompt, LLM method record, raw and object
tables, frozen reproduction code, subject-level comparisons, unmatched-object
audits, annotation comparisons, MAD failures, and paired scaling deltas.

```bash
PYTHONPATH=. python experiments/bidmc_llm_capture/multi_subject_comparison.py \
  --subjects 1-53 --jobs 4 --scaling absolute \
  --output-directory experiments/bidmc_llm_capture/results/multi_subject

PYTHONPATH=. python experiments/bidmc_llm_capture/multi_subject_comparison.py \
  --subjects 1-53 --jobs 4 --scaling mad \
  --output-directory experiments/bidmc_llm_capture/results/mad_multi_subject

PYTHONPATH=. python \
  experiments/bidmc_llm_capture/compare_scaling_runs.py
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
4. Habib, N. *FeatureGraph*, version 0.1.0a1, 2026.
   [https://doi.org/10.5281/zenodo.21535661](https://doi.org/10.5281/zenodo.21535661).
