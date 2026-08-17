# Exact-plateau midpoint experiment

## Question

Do the severe comparison failures on BIDMC subjects 35, 38, and 39 reflect
missed respiratory cycles, or incompatible conventions for assigning a point
timestamp to a flat extremum?

This is a post hoc diagnostic developed after inspecting those subjects. It
does not replace the frozen study and is not untouched confirmatory evidence.

## Fixed experimental change

The rolling envelope, directional states, transition events, cycle identities,
and matching tolerance remain unchanged. For every subject, each exact
constant-valued run containing an already detected peak or trough is represented
as a bounded plateau. Its canonical point is

`plateau_start + floor((plateau_end - plateau_start) / 2)`.

This matches SciPy's documented midpoint convention for even-length flat peaks.
No amplitude threshold, subject identifier, annotation, or baseline peak is
used to form the interval. Original event count is invariant: both constructions
produce 8,205 detected peak events across the 53 subjects.

The midpointed peak and trough indices are used to recompute period and temporal
symmetry. Raw within-object minimum and maximum continue to determine full
excursion. Strict boundary order is then reapplied. Forty-seven formerly
complete candidates become partial/ambiguous because a midpointed peak and
neighboring trough collapse into the same exact flat run. The ambiguity table
contains 100 rows in total: 53 were already partial endpoint fragments and 47
were newly excluded from complete-object metrics. Both counts are reported
separately from the unchanged detected-event count.

## Full-cohort result

| Measure | Envelope leading-edge anchor | Plateau midpoint | Delta |
| --- | ---: | ---: | ---: |
| Detected peak events | 8,205 | 8,205 | 0 |
| Complete FeatureGraph objects | 8,180 | 8,133 | -47 ambiguous |
| Baseline complete objects | 7,168 | 7,168 | 0 |
| Matched objects | 6,513 | 7,086 | +573 |
| FeatureGraph-only objects | 1,667 | 1,047 | -620 |
| Baseline-only objects | 655 | 82 | -573 |
| Median subject FeatureGraph matched fraction | 88.80% | 94.44% | +5.64 points |
| Median subject baseline matched fraction | 100% | 100% | 0 |
| Median absolute peak error | 16 samples | 6.5 samples | -9.5 samples |
| 90th-percentile absolute peak error | 45 samples | 24 samples | -21 samples |
| Median absolute period error | 0.080 s | 0.056 s | -0.024 s |
| Median absolute full-excursion error | 0 | 0 | 0 |
| Median absolute temporal-symmetry error | 0.0943 | 0.0967 | +0.0025 |

Object matches improve for 21 subjects, remain unchanged for 31, and decline
by one match for subject 36. Thus, the gain is concentrated rather than a
uniform rematching artifact, and amplitude agreement is unchanged. Symmetry
does not improve at cohort level, indicating that a midpoint convention solves
extremum timing but not the entire phase-boundary contract.

## Previously severe subjects

| Subject | Matched before | Matched after | Baseline matched after | Median peak error before | Median peak error after |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 30 | 74 | 93.7% | 20 | 38 |
| 35 | 22 | 119 | 98.3% | 52 | 1 |
| 38 | 44 | 125 | 96.2% | 33 | 7 |
| 39 | 0 | 52 | 96.3% | — | 7.5 |

Subjects 35, 38, and 39 therefore were primarily plateau-anchor failures, not
missed-cycle failures. Subject 5 remains a distinct over-segmentation and
signal-quality problem: 89 complete FeatureGraph objects remain unmatched even
though 74 of 79 baseline objects now match.

## Annotation check

Across both BIDMC annotation columns, midpointing substantially improves
alignment while preserving the detected-event count:

| Measure | Leading edge | Midpoint | Delta |
| --- | ---: | ---: | ---: |
| Annotator 1: detected peaks matched | 76.03% | 85.36% | +9.34 points |
| Annotator 1: reference peaks matched | 85.59% | 96.10% | +10.51 points |
| Annotator 2: detected peaks matched | 79.74% | 88.62% | +8.87 points |
| Annotator 2: reference peaks matched | 88.65% | 98.51% | +9.86 points |

For subject 39, 113 of 113 FeatureGraph detections match each annotator; each
annotation series contains one additional reference peak. Subject 35 reaches
139/142 and 138/140 annotation matches. Subject 38 reaches 117/122 and 127/128.

## Interpretation

The experiment supports representing extrema as intervals with optional
canonical point projections. A transition boundary and a peak timestamp are
not necessarily the same event: exiting rising marks the beginning of a flat
maximum, while midpoint projection supports conventional point-based matching.
The saved object schema retains each original transition anchor, both edges of
each peak and trough interval, the midpoint projection, and an explicit causal
`peak_detection_index`. The latter equals the peak-interval end plus the
100-sample envelope-alignment delay, so offline event time is never presented
as zero-latency real-time detection.

This adapter is defensible as a deterministic representation correction, but
it should remain labeled exploratory until frozen and evaluated on a new cohort
or dataset. It does not address subject 5's remaining excess cycles and should
not be presented as a general signal-quality solution.

## Reproduction

```bash
python experiments/bidmc_llm_capture/multi_subject_comparison.py \
  --subjects 1-53 \
  --construction envelope_plateau \
  --output-directory \
    experiments/bidmc_llm_capture/results/envelope_plateau_multi_subject
```

Exact audit tables are stored under
`results/envelope_plateau_multi_subject/`. The stable downstream handoff is
`detector_discordant_episodes.csv`; it labels detector disagreement and burst
context while leaving clinical interpretation explicitly unassigned.
