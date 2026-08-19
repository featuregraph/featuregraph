# BIDMC respiration representation study results

**Corrected run date:** 2026-08-18  
**Executable study record:** [`notebooks/transition_wave copy.ipynb`](../../../notebooks/transition_wave%20copy.ipynb)  
**Numerical-boundary fix:** [`a12cf8d`](https://github.com/featuregraph/featuregraph/commit/a12cf8d04d4485d1def36c44845d54532950b4ef)

## Software correction

Inspection of BIDMC subject 13 exposed a software defect in the exact-zero directional boundary. A numerically flat portion of the rolling mean alternated by `5.551115e-17`, causing repeated rising, falling, and inactive state transitions and approximately twenty spurious object identifiers in one short interval.

The next-smallest observed data-scale envelope change in that interval was approximately `9.7e-06`. The implementation now uses a fixed absolute numerical tolerance of `1e-12`:

```python
respiration_rising = respiration_change > 1e-12
respiration_falling = respiration_change < -1e-12
respiration_inactive = respiration_change.abs() <= 1e-12
```

The same tolerance defines numerically flat extremum runs. This is a floating-point stability boundary, not a physiological amplitude threshold or a subject-specific study parameter.

The `Transition` implementation also now passes its caller-supplied `eps` value to the state operator instead of hard-coding zero. A regression fixture uses the observed `5.551115e-17` residue and a genuine `9.7e-06` change.

### Effect of the correction

| Measure | Exact-zero output | Corrected output | Change |
| --- | ---: | ---: | ---: |
| Detected FeatureGraph peaks | 8,205 | 7,988 | -217 |
| Complete FeatureGraph objects | 8,133 | 7,926 | -207 |
| Matched objects | 7,086 | 7,086 | 0 |
| FeatureGraph-only objects | 1,047 | 840 | -207 |
| Comparator-only objects | 82 | 82 | 0 |
| Ambiguous plateau objects | 100 | 90 | -10 |
| Invalidated complete objects | 47 | 37 | -10 |

All previously matched objects remain matched, and the comparator output is unchanged. The correction removes objects created by numerical chatter without changing the frozen comparator, smoothing window, matching tolerance, or subject-specific rules.

The exact-zero totals above are retained as historical outputs of the defective software version. The corrected totals below are the current regression baseline.

## Study contract

The notebook is the sole executable workflow for this BIDMC study. It retrieves BIDMC 1.0.0 subjects 1–53, constructs a max–then–mean respiratory envelope, derives directional states and transition events, projects numerically flat extremum intervals to their floor midpoints, constructs bounded oscillation objects, and compares them with the frozen SciPy baseline.

The FeatureGraph construction uses a fixed 100-sample window at 125 Hz and a numerical absolute tolerance of `1e-12` for every subject. Ordered object matching uses a frozen tolerance of 63 samples. No subject-specific tuning is performed.

SciPy is used only in the frozen comparator path. The FeatureGraph construction uses explicit pandas operations.

## Corrected 53-subject results

| Measure | Result |
| --- | ---: |
| Subjects completed | 53/53 |
| Failures | 0 |
| Detected FeatureGraph peaks | 7,988 |
| Complete FeatureGraph objects | 7,926 |
| Complete comparator objects | 7,168 |
| Matched objects | 7,086 |
| FeatureGraph-only objects | 840 |
| Comparator-only objects | 82 |
| Ambiguous plateau objects | 90 |
| Formerly complete objects invalidated by overlapping plateau intervals | 37 |
| Median subject FeatureGraph matched fraction | 96.69% |
| Median subject comparator matched fraction | 100% |

### Matched-object differences

The following differences are calculated over the 7,086 matched object pairs.

| Property | Median absolute difference |
| --- | ---: |
| Peak location | 6.5 samples (0.052 seconds) |
| Derived respiratory rate | 0.311 breaths/minute |
| Period | 0.056 seconds |
| Full excursion | 0 |
| Temporal symmetry | 0.0966 |

The 90th-percentile absolute peak-location difference is 24 samples, or 0.192 seconds.

## Subject 1 window sensitivity

| Window (samples) | Effective support | Detected peaks | Complete objects | Matched | FeatureGraph-only | Comparator-only | Invalidated |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 75 | 149 | 170 | 169 | 169 | 0 | 0 | 0 |
| 100 | 199 | 170 | 169 | 169 | 0 | 0 | 0 |
| 125 | 249 | 170 | 169 | 169 | 0 | 0 | 0 |

All three windows now preserve identical subject-1 counts. Their median absolute period difference is 0.056 seconds. Window 100 retains the smallest temporal-symmetry difference of the three.

## Localization of corrected FeatureGraph-only objects

The largest remaining concentrations are:

| Subject | FeatureGraph-only objects |
| ---: | ---: |
| 13 | 114 |
| 5 | 66 |
| 14 | 63 |
| 33 | 61 |
| 39 | 60 |
| 19 | 52 |
| 46 | 43 |
| 27 | 38 |
| 23 | 35 |
| 40 | 25 |

For subject 13, FeatureGraph-only objects fall from 136 to 114 after removal of numerical chatter. Remaining disagreement is not assigned a clinical interpretation.

## BIDMC annotation comparison

Of the 840 corrected FeatureGraph-only objects:

- 474 are excluded by both BIDMC annotation series.
- 366 are retained by at least one annotation series.

| Annotation comparison | Annotator 1 | Annotator 2 |
| --- | ---: | ---: |
| FeatureGraph detected peaks | 7,988 | 7,988 |
| Reference peaks | 7,288 | 7,381 |
| Matched peaks | 7,003 | 7,271 |
| Detected-peak matched fraction | 87.67% | 91.02% |
| Reference-peak matched fraction | 96.09% | 98.51% |

Unmatched and annotation-discordant objects remain labeled computational objects. No clinical interpretation is assigned.

## Regression status

The complete corrected notebook was executed from its first cell through its final cell. All 53 subjects completed, the subject-13 chatter assertion passed, and the frozen regression contract reported:

```text
All frozen BIDMC regression checks passed.
```

The current asserted totals are:

```python
expected = {
    "subjects": 53,
    "failures": 0,
    "featuregraph_detected_peaks": 7988,
    "featuregraph_complete_objects": 7926,
    "baseline_complete_objects": 7168,
    "matched_objects": 7086,
    "featuregraph_only_objects": 840,
    "baseline_only_objects": 82,
    "featuregraph_ambiguous_objects": 90,
    "featuregraph_invalidated_complete_objects": 37,
    "featuregraph_only_excluded_by_both_annotators": 474,
    "featuregraph_only_retained_by_one_or_both_annotators": 366,
}
```
