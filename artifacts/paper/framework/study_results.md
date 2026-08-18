# BIDMC respiration representation study results

**Run date:** 2026-08-18  
**Executable study record:** [`notebooks/transition_wave copy.ipynb`](../../../notebooks/transition_wave%20copy.ipynb)  
**Notebook implementation commit:** [`82f70fe`](https://github.com/featuregraph/featuregraph/commit/82f70fe6905c72a9390290614edd30474ea90018)

## Study contract

The notebook is the sole executable workflow for this BIDMC study. It retrieves BIDMC 1.0.0 subjects 1–53, constructs a max–then–mean respiratory envelope, derives directional states and transition events, projects exact extremum plateaus to their floor midpoints, constructs bounded oscillation objects, and compares them with the frozen SciPy baseline.

The FeatureGraph construction uses a fixed 100-sample window at 125 Hz for every subject. Ordered object matching uses a frozen tolerance of 63 samples. No subject-specific tuning is performed.

SciPy is used only in the frozen comparator path:

```python
from scipy.signal import butter, find_peaks, sosfiltfilt
```

The FeatureGraph construction itself uses explicit pandas operations.

## Full 53-subject results

| Measure | Result |
| --- | ---: |
| Subjects completed | 53/53 |
| Failures | 0 |
| Detected FeatureGraph peaks | 8,205 |
| Complete FeatureGraph objects | 8,133 |
| Complete comparator objects | 7,168 |
| Matched objects | 7,086 |
| FeatureGraph-only objects | 1,047 |
| Comparator-only objects | 82 |
| Ambiguous plateau objects | 100 |
| Formerly complete objects invalidated by overlapping plateau intervals | 47 |
| Median subject FeatureGraph matched fraction | 94.44% |
| Median subject comparator matched fraction | 100% |

### Matched-object differences

The following differences are calculated over the 7,086 matched object pairs.

| Property | Median absolute difference |
| --- | ---: |
| Peak location | 6.5 samples (0.052 seconds) |
| Derived respiratory rate | 0.313 breaths/minute |
| Period | 0.056 seconds |
| Full excursion | 0 |
| Temporal symmetry | 0.0967 |

The 90th-percentile absolute peak-location difference is 24 samples, or 0.192 seconds.

## Subject 1 development record

Subject 1 produced 170 detected FeatureGraph peaks, 169 complete FeatureGraph objects, and 169 comparator objects. All 169 complete objects matched. Neither method produced an unmatched complete object.

| Property | FeatureGraph mean | Comparator mean | Median absolute difference |
| --- | ---: | ---: | ---: |
| Period | 2.8216 seconds | 2.8213 seconds | 0.056 seconds |
| Derived respiratory rate | 21.396 breaths/minute | 21.371 breaths/minute | 0.436 breaths/minute |
| Full excursion | 0.9030 | 0.9027 | 0.00489 |
| Temporal symmetry | 0.9244 | 0.8438 | 0.0971 |

## Subject 1 window sensitivity

| Window (samples) | Effective support (samples) | Detected peaks | Complete objects | Matched objects | FeatureGraph-only | Comparator-only | Invalidated |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 75 | 149 | 172 | 170 | 169 | 1 | 0 | 1 |
| 100 | 199 | 170 | 169 | 169 | 0 | 0 | 0 |
| 125 | 249 | 170 | 169 | 169 | 0 | 0 | 0 |

Windows 100 and 125 preserve identical subject-1 object counts. Window 100 has the lowest temporal-symmetry difference of the three. Window 75 introduces two additional detected peaks and one unmatched complete object.

## Localization of FeatureGraph-only objects

The 1,047 FeatureGraph-only objects occur in 46 of 53 subjects, but they are substantially concentrated.

| Subject | FeatureGraph-only objects |
| ---: | ---: |
| 13 | 136 |
| 19 | 92 |
| 5 | 89 |
| 14 | 63 |
| 33 | 61 |
| 39 | 60 |
| 27 | 54 |
| 23 | 48 |
| 46 | 43 |
| 25 | 32 |

The five largest subject concentrations contain 441 objects, or 42.1% of all FeatureGraph-only objects. The ten largest contain 678 objects, or 64.8%.

These rows represent detector disagreement, not established false detections or clinical diagnoses.

## BIDMC annotation comparison

Of the 1,047 FeatureGraph-only objects:

- 680 are excluded by both BIDMC annotation series.
- 367 are retained by at least one annotation series.

| Annotation comparison | Annotator 1 | Annotator 2 |
| --- | ---: | ---: |
| FeatureGraph detected peaks | 8,205 | 8,205 |
| Reference peaks | 7,288 | 7,381 |
| Matched peaks | 7,004 | 7,271 |
| Detected-peak matched fraction | 85.36% | 88.62% |
| Reference-peak matched fraction | 96.10% | 98.51% |

The unmatched and annotation-discordant objects remain labeled computational objects. No clinical interpretation is assigned.

## Regression status

The complete notebook was executed from its first cell through its final cell after the implementation change. All 53 subjects completed, and the final frozen regression contract passed:

```text
All frozen BIDMC regression checks passed.
```

The asserted totals are:

```python
expected = {
    "subjects": 53,
    "failures": 0,
    "featuregraph_detected_peaks": 8205,
    "featuregraph_complete_objects": 8133,
    "baseline_complete_objects": 7168,
    "matched_objects": 7086,
    "featuregraph_only_objects": 1047,
    "baseline_only_objects": 82,
    "featuregraph_ambiguous_objects": 100,
    "featuregraph_invalidated_complete_objects": 47,
    "featuregraph_only_excluded_by_both_annotators": 680,
    "featuregraph_only_retained_by_one_or_both_annotators": 367,
}
```
