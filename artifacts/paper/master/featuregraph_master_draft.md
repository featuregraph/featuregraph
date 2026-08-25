# From Agreement Counts to Inspectable Disagreement: An Auditable Respiratory-Object Study on BIDMC

**Nazia Habib**

**FeatureGraph**

**arXiv draft — August 25, 2026**

## Abstract

Time-series studies often reduce agreement between two computational methods to a single score, leaving it difficult to determine where disagreement occurs, which records produce it, and whether discordant events form one coherent error category. We present a deterministic, object-level respiratory waveform study on all 53 records in the public BIDMC PPG and Respiration Dataset. A researcher-authored contract defines preprocessing, directional states, transition events, plateau-aware boundaries, trough-peak-trough object identity, measurements, a frozen SciPy comparator, matching, validation, and interpretation limits. A generated workflow executes that contract independently for every record and retains observation-, event-, object-, comparison-, annotation-, and provenance-level evidence.

The workflow produced 7,926 complete FeatureGraph objects and 7,168 complete comparator objects. Ordered one-to-one matching associated 7,086 pairs within 63 samples; 840 objects were FeatureGraph-only and 82 were comparator-only. The median absolute peak-location difference among matched pairs was 6.5 samples (0.052 s). The 840 FeatureGraph-only objects were strongly concentrated: the seven highest-contributing subjects accounted for 459 objects (54.6%), and the ten highest accounted for 557 (66.3%). Their annotation relationships were heterogeneous. Of all FeatureGraph-only objects, 474 were excluded by both independent annotation series and 366 were retained by at least one. Among the largest contributing records, subject 5 had 63 of 66 objects excluded by both annotations, subject 39 had all 60 retained by at least one, and subject 13 had 40 of 114 excluded and 74 retained. The unmatched population therefore cannot be interpreted uniformly as either additional valid breaths or false detections.

A numerical-boundary investigation further showed that floating-point residue near \(5.55\times10^{-17}\) could create repeated state changes under exact-zero comparisons. Declaring a numerical tolerance of \(10^{-12}\) removed 207 spurious complete unmatched objects without changing any of the 7,086 matched pairs. A bounded deterministic compiler now executes the directional-state and enter/exit-event layer from the researcher contract, while independent parity checks protect the previously frozen formulas. This study does not establish clinical validity or respiratory ground truth. It demonstrates that explicit construction contracts and retained object-level evidence can turn aggregate disagreement into a reproducible, localized, and scientifically reviewable result.

## 1. Introduction

Respiratory waveform analysis requires a chain of representational decisions before any event can be counted. A researcher must select a signal, choose a preprocessing frame, define what constitutes directional change, decide how flat extrema are handled, identify which events bound a candidate waveform, determine completeness, and choose how two constructions will be compared. When those decisions are embedded across notebook cells and helper functions, the final count does not fully describe the analysis. The same output may conceal different boundary rules, and the same disagreement count may combine several distinct phenomena.

This problem becomes especially important when a study uses computational assistance to expand a compact scientific specification into cohort-scale code. Repetition, file checking, matching, aggregation, and reporting can be automated, but scientific rules should not enter silently through the execution layer. A reproducible workflow must therefore preserve both the result and the authority boundary: which decisions were supplied by the researcher, which operations mechanically execute them, and which interpretations remain unsupported.

FeatureGraph is a deterministic representation framework for constructing explicit behavioral objects from ordered observations. In the present study, an object is not assumed to be a clinically validated breath. It is a computational trough-peak-trough waveform defined by a declared signal construction. Each object retains its source record, supporting indices, boundary intervals, completeness and ambiguity flags, measurements, comparison status, and annotation relationships. This makes agreement and disagreement inspectable below the cohort total.

We apply this workflow to the BIDMC PPG and Respiration Dataset, which contains 53 eight-minute clinical recordings sampled at 125 Hz and two independently produced breath-annotation series [1,2]. The study uses the impedance respiration signal, not the photoplethysmogram, and asks a deliberately bounded question:

> Can a researcher-authored respiratory-object construction be executed across the complete BIDMC cohort while preserving enough evidence to reproduce, localize, and interpret the limits of agreement with a frozen comparator?

The primary contribution is not a claim that FeatureGraph detects more valid breaths. It is a method and empirical result showing that the 840 FeatureGraph-only objects are concentrated in a subset of records and divide differently with respect to the two annotation series. Aggregate disagreement therefore contains record-specific structure that would be lost if all unmatched objects were assigned a single label.

The contributions of this study are:

1. an explicit researcher-authored contract for a respiratory waveform construction, comparator, matching rule, validation requirements, and claim boundaries;
2. a reproducible workflow that executes the construction independently across all 53 BIDMC records and retains observations, states, events, objects, comparisons, annotations, and provenance;
3. a cohort-level comparison comprising 7,926 complete FeatureGraph objects, 7,168 complete comparator objects, and 7,086 matched pairs;
4. a subject-level analysis showing that 54.6% of the 840 FeatureGraph-only objects arise from seven subjects and that the highest-contributing records have sharply different annotation patterns;
5. a documented numerical-boundary correction that removes floating-point-induced identities without changing any matched pair; and
6. a bounded deterministic compiler integration for the directional-state and transition-event layer, protected by per-record parity assertions.

## 2. Materials and methods

### 2.1 Dataset

We used version 1.0.0 of the public BIDMC PPG and Respiration Dataset [1]. The dataset contains 53 eight-minute recordings acquired during hospital care at Beth Israel Deaconess Medical Center. Physiological waveforms are sampled at 125 Hz. The present study uses the impedance respiration signal supplied in the CSV distribution. Each record also includes two independent series of manually identified breath annotations.

All 53 records were included. The workflow expected 60,001 signal rows per record, required the respiration column, rejected missing respiration values, and executed each record independently. The raw respiration signal was retained unchanged alongside every derived column.

The original dataset was assembled to support research on respiratory-rate estimation from pulse oximetry [2]. The present analysis does not reproduce that respiratory-rate algorithm and does not evaluate photoplethysmographic respiratory-rate estimation. It uses the supplied impedance respiratory waveform and annotations to study explicit waveform construction and disagreement.

### 2.2 Researcher-authored study contract

The authoritative researcher input is a single executable notebook cell. It declares:

- subjects 1 through 53;
- sampling rate and expected record dimensions;
- raw-signal preservation;
- preprocessing and temporal alignment;
- numerical precision;
- rising, falling, and inactive states;
- enter- and exit-state events;
- plateau-aware extrema and representative points;
- trough-peak-trough identity and completeness;
- object measurements;
- the external comparator and one-to-one matching rule;
- comparison with both annotation series;
- required cohort, subject, object, and sensitivity outputs;
- validation assertions; and
- supported and unsupported interpretations.

The generated workflow may implement downloading, integrity checks, repetition, assembly, matching, aggregation, provenance, and reporting. It may not change a threshold, filter, boundary, identity, completeness rule, matching rule, measurement, exclusion, imputation, or scientific interpretation without changing the researcher contract.

### 2.3 FeatureGraph signal construction

For each subject, the raw respiration sequence \(x_t\) was preserved. A separate offline envelope was formed by a 100-sample rolling maximum followed by a 100-sample rolling mean and an alignment shift of \(-100\) samples. The combined rolling operations have an effective support of 199 samples, approximately 1.592 s at 125 Hz. Because the alignment uses future observations, this construction is non-causal and is not presented as an online detector.

Let \(y_t\) denote the aligned envelope and

\[
\Delta y_t = y_t-y_{t-1}.
\]

The numerical tolerance was fixed at \(\epsilon=10^{-12}\). Valid samples were assigned one of three mutually exclusive states:

\[
s_t=
\begin{cases}
\text{rising}, & \Delta y_t > \epsilon,\\
\text{falling}, & \Delta y_t < -\epsilon,\\
\text{inactive}, & |\Delta y_t|\leq \epsilon.
\end{cases}
\]

The tolerance is numerical, not physiological. It distinguishes directional change from floating-point residue after preprocessing; it does not define a minimum respiratory amplitude.

Entering the rising state defines a trough-side transition, and exiting the rising state defines a peak-side transition. Because the directional state describes the edge ending at the current sample, the entering-rising event is projected one sample backward to the trough. The exiting-rising event is already located on the peak sample.

### 2.4 Plateau-aware boundaries and object identity

Numerically flat extrema were represented as intervals rather than immediately collapsed to points. A complete plateau interval was projected to the floor of its midpoint for comparison and measurement. The interval itself remained available for ambiguity and overlap checks.

One candidate object was defined by a starting trough, an interior peak, and a following trough. A complete object required:

1. all three boundaries;
2. strict temporal ordering;
3. complete leading and trailing boundary support; and
4. non-overlapping projected plateau intervals.

Incomplete, truncated, plateau-ambiguous, and invalidated candidates remained represented with explicit flags. Complete objects were measured for period, derived rate, full excursion, and temporal symmetry. Measurements were calculated only after identity and boundaries had been established.

### 2.5 Deterministic compiler boundary

The researcher contract contains a versioned `state-contract-v1` mapping. The deterministic compiler consumes the declared input columns and state expressions, validates state exclusivity and exhaustiveness, assigns state-occurrence identities, and materializes requested entering- and exiting-rising events.

The compiler integration is deliberately bounded. It compiles directional states and their enter/exit boundaries. It does not currently compile preprocessing, plateau projection, trough-peak-trough identity, object measurements, comparison, aggregation, or scientific interpretation. Those layers remain explicit generated-study Python.

For every BIDMC record, independent parity assertions compare the compiler-produced states and event locations with the study's previously frozen deterministic formulas. The workflow stores the canonical contract as JSON and records its SHA-256 fingerprint in provenance. This establishes output parity and traceability for a narrow layer; it does not prove semantic equivalence of the entire generated notebook.

### 2.6 Frozen SciPy comparator

The comparator was specified before cohort execution and remained unchanged. It operated on the raw respiration signal using:

- a fourth-order Butterworth low-pass filter with a 0.8 Hz cutoff;
- zero-phase `sosfiltfilt` filtering;
- `scipy.signal.find_peaks` for peaks and troughs;
- a minimum peak distance of 188 samples; and
- a minimum prominence of 0.08.

Consecutive comparator troughs surrounding a comparator peak defined a complete comparator object. SciPy provides the numerical filtering and peak-finding implementation [3]; the comparator settings and object assembly are study-specific and are not presented as universal respiratory ground truth.

### 2.7 Ordered one-to-one matching

FeatureGraph and comparator objects were matched by their representative peak indices. A candidate match required an absolute peak difference no greater than 63 samples, approximately 0.504 s. Matching was ordered and one-to-one so that no object could be paired more than once and temporal ordering could not be reversed.

Objects were then classified as:

- **matched:** assigned to one object from the other construction;
- **FeatureGraph-only:** no comparator match within the declared rule; or
- **comparator-only:** no FeatureGraph match within the declared rule.

These labels describe agreement between two computational constructions. They are not truth labels.

### 2.8 Annotation comparison

The two BIDMC annotation series were treated as independent external reference points. For each FeatureGraph-only object, its representative peak was compared with each annotation series under the study's declared tolerance. An object was classified as excluded by both annotations only when neither annotation series retained it. Otherwise it was classified as retained by one or both.

The annotation comparison was not used to redefine the FeatureGraph construction or comparator after results were observed. Nor were the annotation series assumed to provide infallible ground truth for every discordant waveform.

### 2.9 Validation and reproducibility

The workflow validated:

- all 53 expected subjects;
- 60,001 rows and a non-missing respiration signal in every record;
- independent per-subject state and identity construction;
- unchanged raw respiration values;
- mutually exclusive and exhaustive valid states;
- parity between compiled and frozen state/event formulas;
- object boundary ordering and completeness;
- one-to-one ordered matching;
- declared cohort regression counts;
- the numerical-boundary regression fixture; and
- software, repository, notebook, and contract provenance.

The complete rerun used repository commit `eeb9d5e193a23bce369faec37a207c6e1ff91e01`. It recorded researcher-input SHA-256 `e2dad5d307fd1101f847e591fbc50fc1c11eea6738a433e663948a9c39048b5a`, execution-notebook SHA-256 `cd79bb0b9b9f823f90cb6b188099f3c6295b83884256bab6431da1b317fbb229`, and state-contract SHA-256 `043c8c35d895f81ac5dc5d81313e5581f3ede6136e49f7da842a072c451f6669`.

The recorded execution environment used Python 3.12.13, pandas 2.2.3, NumPy
2.3.5, and SciPy 1.17.0 on 64-bit Linux.

## 3. Results

### 3.1 Complete cohort execution

All 53 records completed with no execution failures. Every source signal passed the declared integrity checks, and 53 per-subject observation/state/event tables were written.

| Output | Count |
| --- | ---: |
| FeatureGraph peak events | 7,988 |
| Complete FeatureGraph objects | 7,926 |
| Complete comparator objects | 7,168 |
| Matched object pairs | 7,086 |
| FeatureGraph-only objects | 840 |
| Comparator-only objects | 82 |
| Plateau-ambiguous FeatureGraph objects | 90 |
| Formerly complete candidates invalidated by overlapping plateaus | 37 |

The object counts satisfy the comparison identities

\[
7{,}926 = 7{,}086 + 840
\]

and

\[
7{,}168 = 7{,}086 + 82.
\]

At the cohort level, 89.4% of complete FeatureGraph objects were matched, while 98.9% of complete comparator objects were matched. These fractions are directional agreement summaries, not sensitivity or positive predictive value, because neither construction is designated as ground truth.

The median subject-level matched fractions were 96.7% for FeatureGraph objects
and 100% for comparator objects. The difference between the 89.4% pooled
FeatureGraph fraction and the 96.7% median subject fraction is consistent with
the unmatched population being concentrated in a subset of records.

### 3.2 Agreement among matched objects

Across the 7,086 matched pairs, the median absolute peak-location difference was 6.5 samples, equivalent to 0.052 s at 125 Hz. The 90th percentile absolute peak-location difference was 24 samples (0.192 s).

| Matched-object property | Median absolute difference |
| --- | ---: |
| Peak location | 6.5 samples (0.052 s) |
| Derived rate | 0.311 breaths/min |
| Period | 0.056 s |
| Full excursion | 0 |
| Temporal symmetry | 0.0966 |

These comparisons show that the two constructions often identify nearby peaks and similar bounded measurements when they match. They do not establish interchangeability: 922 complete objects remain unmatched across the two constructions.

### 3.3 FeatureGraph-only objects were concentrated by subject

The 840 FeatureGraph-only objects were not uniformly distributed across the cohort. Seven subjects produced no FeatureGraph-only objects. At the other extreme, subject 13 produced 114, or 13.6% of the cohort total.

| Rank | Subject | FeatureGraph-only objects | Share of all 840 | Cumulative share |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 13 | 114 | 13.6% | 13.6% |
| 2 | 5 | 66 | 7.9% | 21.4% |
| 3 | 14 | 63 | 7.5% | 28.9% |
| 4 | 33 | 61 | 7.3% | 36.2% |
| 5 | 39 | 60 | 7.1% | 43.3% |
| 6 | 19 | 52 | 6.2% | 49.5% |
| 7 | 46 | 43 | 5.1% | 54.6% |
| 8 | 27 | 38 | 4.5% | 59.2% |
| 9 | 23 | 35 | 4.2% | 63.3% |
| 10 | 40 | 25 | 3.0% | 66.3% |

The top five subjects accounted for 364 objects (43.3%), the top seven for 459 (54.6%), and the top ten for 557 (66.3%). Concentration is therefore a cohort result, not an impression based on isolated visual examples.

The relative within-subject disagreement was also high in several leading records. FeatureGraph-only objects constituted 52.1% of subject 13's complete FeatureGraph objects, 47.1% of subject 5's, 38.9% of subject 14's, 36.3% of subject 33's, and 53.6% of subject 39's. The overall population is thus driven both by records with many constructed objects and by records in which the two constructions differ over a large portion of the waveform.

### 3.4 High-contributing subjects had different annotation patterns

Of the 840 FeatureGraph-only objects, 474 (56.4%) were excluded by both annotation series and 366 (43.6%) were retained by at least one. The division varied sharply across the highest-contributing subjects.

| Subject | FeatureGraph-only | Excluded by both | Retained by at least one | Excluded by both |
| ---: | ---: | ---: | ---: | ---: |
| 13 | 114 | 40 | 74 | 35.1% |
| 5 | 66 | 63 | 3 | 95.5% |
| 14 | 63 | 39 | 24 | 61.9% |
| 33 | 61 | 53 | 8 | 86.9% |
| 39 | 60 | 0 | 60 | 0.0% |
| 19 | 52 | 42 | 10 | 80.8% |
| 46 | 43 | 30 | 13 | 69.8% |
| 27 | 38 | 19 | 19 | 50.0% |
| 23 | 35 | 30 | 5 | 85.7% |
| 40 | 25 | 12 | 13 | 48.0% |

The contrast between subjects 5, 13, and 39 is especially informative. Nearly every FeatureGraph-only object in subject 5 was excluded by both annotation series. Every FeatureGraph-only object in subject 39 was retained by at least one. Subject 13, the largest contributor, contained substantial populations of both types. A single cohort-wide label for the 840 objects would therefore combine qualitatively different patterns of external agreement.

The top ten subjects contained 328 of the 474 objects excluded by both annotations (69.2%) and 229 of the 366 retained by at least one (62.6%). Concentration is present in both annotation categories; it is not produced solely by one type of disagreement.

### 3.5 Numerical-boundary correction localized a deterministic failure

Subject 13 exposed changes near \(5.55\times10^{-17}\) in an envelope region that was numerically, but not bitwise, flat. With an exact-zero comparison, those values repeatedly crossed the rising/falling boundary and created spurious state occurrences and object identities.

The researcher contract was revised to declare \(\epsilon=10^{-12}\) as a numerical tolerance. A regression fixture distinguishes the observed residue from a genuine envelope change near \(9.7\times10^{-6}\). Relative to the exact-zero construction, the tolerance removed 207 complete FeatureGraph-only objects without changing any of the 7,086 matched pairs.

This correction is evidence for the value of an inspectable state/event layer. The failure could be located at the numerical boundary, classified as numerical rather than physiological, repaired in the authoritative contract, and protected by a regression assertion. It was not treated as a reason to tune the comparator or redefine unmatched objects after cohort evaluation.

## 4. Discussion

### 4.1 What the 840 objects establish

FeatureGraph found 840 complete objects that were not matched to the frozen comparator. This number alone does not show that FeatureGraph detects more valid breaths, nor does it show that FeatureGraph produces 840 false detections. The annotation analysis rules out either uniform interpretation: 474 objects were excluded by both annotation series, while 366 were retained by at least one.

The subject-level analysis adds a second constraint on interpretation. Disagreement is concentrated, but the largest contributing subjects differ sharply. Subject 5 resembles a record in which FeatureGraph constructs many waveforms not supported by either annotation series. Subject 39 resembles a record in which the comparator omits many FeatureGraph objects that at least one annotation series retains. Subject 13 contains both populations. These are hypotheses about computational and annotation relationships, not physiological diagnoses. Representative signal-level inspection is required before assigning morphology or cause.

The scientifically supported contribution is therefore **inspectable disagreement**. The workflow identifies which records dominate disagreement, preserves every discordant object's boundaries and measurements, and connects those objects to the underlying signal and both annotation series. This narrows the next scientific question from “Why are there 840 extra objects?” to record- and object-specific questions that can be reviewed directly.

### 4.2 Why object-level evidence changes method comparison

Aggregate agreement is useful but incomplete. A high comparator matched fraction can coexist with a concentrated population of records on which the constructions behave very differently. Conversely, a large unmatched count can contain objects supported by an external annotation series as well as objects unsupported by either series.

An object table makes these cases queryable. Rather than regenerating candidate events from plots, a reviewer can retrieve the exact subject, start, peak, end, plateau intervals, completeness status, measurements, comparator status, annotation status, and source indices. The same representation supports cohort summaries without discarding the evidence needed to challenge them.

This is distinct from claiming that object construction removes scientific judgment. The tables expose where judgment is needed. Whether a discordant waveform represents a breath, artifact, compound respiratory behavior, annotation omission, preprocessing effect, or an unsuitable object definition requires domain analysis beyond the present computational comparison.

### 4.3 Researcher authority and generated execution

The paired workflow separates a compact scientific specification from its mechanical expansion. This is particularly relevant when an LLM assists with code generation. The generated layer may write loops, checks, tables, and reports, but its output is scientifically defensible only if thresholds, boundaries, comparison rules, and interpretations remain attributable to the researcher contract.

The present study implements that separation imperfectly but concretely. The input notebook declares the full study. The runner verifies frozen values, fingerprints the input and execution artifacts, executes all records, writes object-level outputs, and protects expected results through assertions. The state-contract compiler further replaces one segment of duplicated execution logic with a deterministic interpreter of the researcher-authored state mapping.

### 4.4 Meaning of the compiler result

The compiler result is deliberately narrower than a claim of automatic study generation. The compiler currently owns directional-state assignment, state-occurrence identity, and entering/exiting-state events. Independent parity checks show that this layer reproduces the frozen BIDMC formulas on every record.

Preprocessing, plateau handling, respiratory-object identity, measurement, comparison, aggregation, and interpretation remain explicit generated Python. The study therefore demonstrates a bounded compiler-backed vertical slice inside a complete workflow. It does not demonstrate that arbitrary researcher notebooks can be compiled automatically or that declarative metadata proves that an external scientific method executed as claimed.

### 4.5 Numerical precision is part of the representation

The subject 13 correction shows that numerical precision cannot always remain an implicit implementation detail. An exact-zero comparison made machine-scale residue behave as a series of scientific transitions. Once those transitions created object identity, the effect propagated into cohort disagreement.

Declaring the tolerance in the researcher contract made the choice visible and testable. Equally important, the tolerance was explicitly denied physiological meaning. This distinction prevents a numerical repair from being misrepresented as a validated amplitude threshold.

## 5. Limitations

This is a representation and workflow study, not a clinical validation study. The impedance respiratory signal, the SciPy comparator, and the two annotation series provide different external views; none is designated as universal ground truth.

The FeatureGraph envelope is non-causal and uses a fixed 100-sample max-then-mean construction selected for this study. Its behavior may not transfer to other sampling rates, sensors, populations, or real-time use without a separately declared study.

The 63-sample matching tolerance, comparator filtering, minimum distance, and prominence are frozen comparison choices. Different defensible comparators or matching contracts could change the unmatched population. The present contribution is reproducibility and localization under the declared contract, not invariance to all comparison methods.

The annotation analysis only determines whether an unmatched representative peak lies within the declared relationship to each annotation series. It does not adjudicate ambiguous morphology or explain disagreement causally. The terms “excluded” and “retained” describe the declared comparison; they do not certify false and true breaths.

The concentration analysis is descriptive and was performed on the same complete cohort used to report agreement. It was not prospectively hypothesized and should be treated as a result that motivates targeted follow-up, not as an independently confirmed population law.

The highest-contributing subjects have not yet been assigned a validated taxonomy of signal morphology. The contrasts among subjects 5, 13, and 39 identify where such analysis should begin, but the present manuscript does not label the underlying behavior.

The deterministic compiler covers only the state and transition-event layer. Other declarations are protected through explicit code, selected binding checks, artifact hashes, and regression outputs rather than a complete semantic compiler.

Finally, the generated workflow was produced through assisted development. Hashes and parity checks make drift visible but do not prove that every line of generated code is semantically entailed by the researcher input. Stronger typed specifications and broader compiler coverage remain future work.

## 6. Conclusion

A complete rerun of an explicit respiratory-object construction across all 53 BIDMC records produced 7,926 complete FeatureGraph objects, 7,168 comparator objects, and 7,086 ordered one-to-one matches. The remaining 840 FeatureGraph-only objects were not diffuse noise: seven subjects accounted for 54.6%, and ten accounted for 66.3%. Nor were they one annotation category: 474 were excluded by both annotation series and 366 were retained by at least one, with sharply different proportions among the highest-contributing subjects.

The result does not establish that FeatureGraph detects more valid breaths. It establishes that computational disagreement can be preserved in a form that is reproducible, localized, and open to scientific inspection. The numerical-boundary correction and bounded state-contract compiler further show how explicit representations can expose implementation failures and protect a researcher-authored decision boundary during cohort-scale execution.

The immediate next study is not another aggregate detector comparison. It is a targeted analysis of the concentrated subjects and their unmatched waveform morphology, beginning with the contrasting annotation patterns in subjects 5, 13, and 39.

## Code and data availability

The complete study record is available in the public FeatureGraph repository:

- Researcher input: `notebooks/researcher_input/bidmc_researcher_input.ipynb`
- Generated study: `notebooks/generated_study/bidmc_generated_study.ipynb`
- Workflow runner: `scripts/run_bidmc_researcher_workflow.py`
- Study record: `artifacts/studies/bidmc_object_workflow_study.md`
- Deterministic state compiler: `src/featuregraph/contracts/state_contract.py`

The source dataset is publicly available from PhysioNet under its stated access terms and license [1]. Machine-generated observation and object tables are reproducible outputs and are not committed to the source repository.

From the repository root, the workflow is executed with:

```bash
python -m pip install -e .
python scripts/run_bidmc_researcher_workflow.py
```

## Ethics statement

This study uses an existing publicly distributed, de-identified dataset and introduces no new participant recruitment, intervention, or access to identifiable clinical records. Use of the source data remains subject to the dataset's license and terms [1].

## AI-assistance statement

An AI coding and writing assistant was used under researcher direction to help implement, execute, inspect, and draft the study. Scientific definitions, comparison rules, interpretation boundaries, and final responsibility for the manuscript remain with the author. The repository preserves the researcher-authored specification, generated execution artifact, tests, and provenance needed to inspect that division of responsibility.

## References

1. Pimentel MAF, Johnson AEW, Charlton PH, Clifton DA. BIDMC PPG and Respiration Dataset. PhysioNet, version 1.0.0; 2018. doi:[10.13026/C2208R](https://doi.org/10.13026/C2208R).
2. Pimentel MAF, Johnson AEW, Charlton PH, Birrenkott D, Watkinson PJ, Tarassenko L, Clifton DA. Toward a robust estimation of respiratory rate from pulse oximeters. *IEEE Transactions on Biomedical Engineering*. 2017;64(8):1914–1923. doi:[10.1109/TBME.2016.2613124](https://doi.org/10.1109/TBME.2016.2613124).
3. Virtanen P, Gommers R, Oliphant TE, et al. SciPy 1.0: fundamental algorithms for scientific computing in Python. *Nature Methods*. 2020;17:261–272. doi:[10.1038/s41592-019-0686-2](https://doi.org/10.1038/s41592-019-0686-2).
