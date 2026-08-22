# PhysioNet wearable protocol representation study

## Question

Can FeatureGraph preserve and materialize the stress-protocol states and
button-marked boundaries declared by the authors of the PhysioNet *Wearable
Device Dataset from Induced Stress and Structured Exercise Sessions*, while
using the same object schema across the two published protocol versions?

## Source

- Dataset: PhysioNet version 1.0.1
- DOI: [10.13026/he0v-tf17](https://doi.org/10.13026/he0v-tf17)
- Source page: [Wearable Device Dataset](https://physionet.org/content/wearable-device-dataset/1.0.1/)
- Device: Empatica E4
- Selected signals: heart rate, electrodermal activity, and skin temperature

The source dataset contains 18 participants in each of two stress-protocol
versions. The authors' notebook declares the task spans by indexing physical
button presses stored in `tags.csv`. Self-reported stress values are supplied
separately for every named protocol stage.

The notebook narrative describes 12 version-1 tags, while every downloaded
version-1 `tags.csv` contains 13. The notebook's task-span code references only
the first 12 marks and leaves the final mark uninterpreted. This study follows
that executable declaration and does not assign new meaning to the extra mark.

## Representation contract

The source protocol names remain authoritative. FeatureGraph does not infer
stress from the physiological signals.

1. Each source tag remains an external boundary.
2. Named intervals are materialized as baseline, task, or rest occurrences.
3. Reporting and setup gaps not named by the source notebook are represented as
   `unassigned`, rather than silently reclassified.
4. The categorical protocol sequence is compiled with `state-contract-v1`.
5. Native signal samples are summarized inside each declared occurrence without
   interpolation or resampling.
6. Self-reported stress is joined to the corresponding occurrence as an
   externally produced measurement.

## Declared protocol differences

Version 1 contains baseline, Stroop, first rest, TMCT, second rest, real-opinion,
opposite-opinion, and subtraction stages. Version 2 removes Stroop and changes
the order of the two rest periods. These are real source-protocol differences,
so the tag adapters differ while the compiler, object schema, and measurement
equations remain unchanged.

## Source constraints

Three records are excluded according to the dataset authors' constraint file:

- `S02`: duplicated raw signals
- `f07`: PPG and temperature sensors covered by the protection dock
- `f14`: the protocol is split across two recordings after Bluetooth loss

The split `f14` record could be handled by a future explicit composition study;
it is not silently repaired here.

## Results

The completed run included 33 participants and materialized 248 declared
protocol occurrences: 136 from version 1 and 112 from version 2.

- All 248 declared start and end boundaries survived compilation exactly.
- All 248 objects joined losslessly to the corresponding source self-report.
- Every object contained native-rate HR, EDA, and temperature samples.
- All 99 compiler validation checks passed.
- Both protocol versions produced the same object schema and measurements.
- `unassigned` time comprised 3,642 of 23,398 compiled seconds (15.6%) in
  version 1 and 461 of 34,817 seconds (1.3%) in version 2.

The unassigned intervals are a substantive preservation result. Treating every
gap between button presses as part of the neighboring task or rest stage would
have added meaning that the source notebook did not declare.

As a descriptive check rather than a physiological validation, each
participant's task-stage mean was compared with their mean over baseline and
the two rest stages. Self-reported stress was higher for 31 of 33 participants,
with a median within-participant difference of 1.25 points. Median heart rate
was higher for 28 of 33 participants, with a median difference of 4.49 beats per
minute; EDA was higher for 25 of 33 participants, while temperature showed no
similarly consistent direction. These comparisons do not identify stress,
establish causality, or validate a digital biomarker.

## Execution

```bash
python scripts/run_physionet_wearable_protocol_study.py
```

The runner downloads the declared public source files, compiles the protocol
timeline, creates the occurrence table, and writes compressed observation,
object, summary, and validation artifacts under
`outputs/physionet_wearable_protocol/`.

## Validation boundary

The following questions are deterministic:

- Did every declared start and end tag survive exactly?
- Did occurrence identity reconstruct constant protocol-state runs?
- Did both protocol versions produce the same object schema?
- Did every object receive its source self-report and native signal samples?
- Were incomplete or constrained records rejected explicitly?

The following questions still require scientific judgment:

- Did the tasks induce psychological stress?
- Are changes in heart rate, electrodermal activity, or temperature caused by
  stress rather than movement, environment, timing, or other factors?
- Are the protocol stages valid clinical digital biomarkers?
- Should an `unassigned` interval receive a scientific interpretation?

This is therefore a representation and interoperability study, not a stress
detector, efficacy analysis, or physiological validation study.
