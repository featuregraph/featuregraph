# BIDMC rolling-envelope experiment

## Construction

This run replaces the native `diff(45) > 0.15` boundary rule with the fixed
offline construction proposed during the post-study detector audit:

```python
respiration_envelope = (
    respiration.rolling(100).max().rolling(100).mean().shift(-100)
)
rising = respiration_envelope.diff() > 0
peak = exit(rising)
```

All rolling operations are isolated by subject. The envelope determines state
and object boundaries; full excursion is measured from the retained raw
respiration observations within each object. The two 100-sample windows and
100-sample alignment shift are fixed for every subject. No subject-specific
tuning is performed.

The offline shift uses future observations. A causal implementation can
compute the same envelope without the shift, emit the corresponding event 100
samples (0.8 seconds) later, and retain separate event and detection times.

## Subject 1

| Measure | Rolling envelope | Previous native difference rule | Recorded LLM baseline |
| --- | ---: | ---: | ---: |
| Complete objects | 169 | 174 | 169 |
| Matched objects | 169 | 169 | 169 |
| Native-only objects | 0 | 5 | — |
| Baseline-only objects | 0 | 0 | — |
| Mean period | 2.821 s | 2.802 s (matched) | 2.821 s |
| Mean full excursion | 0.903 | 0.896 (matched) | 0.903 |
| Mean temporal symmetry | 0.910 | 0.596 (matched) | 0.844 |
| Median peak-index error | 17 samples | 10 samples | reference |
| Median start/end-index error | 33 samples | 53 samples | reference |
| Median temporal-symmetry error | 0.072 | 0.250 | reference |

The envelope removes all five additional subject-1 objects. Both BIDMC
annotation series match all 170 detected peaks and miss none within the frozen
63-sample tolerance. Median annotation error is 22 samples for annotator 1 and
25 for annotator 2. The previous native rule placed peaks closer to the LLM
baseline, but the envelope places trough boundaries more consistently and
substantially improves symmetry agreement.

## Full 53-subject transfer

| Measure | Rolling envelope | Previous native difference rule | Change |
| --- | ---: | ---: | ---: |
| FeatureGraph complete objects | 8,180 | 8,960 | -780 |
| Baseline complete objects | 7,168 | 7,168 | 0 |
| Matched objects | 6,513 | 6,200 | +313 |
| FeatureGraph-only objects | 1,667 | 2,760 | -1,093 |
| Baseline-only objects | 655 | 968 | -313 |
| Median subject FeatureGraph matched fraction | 88.8% | 78.6% | +10.2 points |
| Median subject baseline matched fraction | 100.0% | 99.1% | +0.9 points |
| Median absolute peak error | 16 samples | 12 samples | +4 samples |
| Median absolute period error | 0.080 s | 0.080 s | unchanged |
| Median absolute symmetry error | 0.094 | 0.352 | -0.258 |
| Ann1 detected-peak matched fraction | 76.0% | 67.5% | +8.5 points |
| Ann2 detected-peak matched fraction | 79.7% | 69.5% | +10.3 points |

The envelope is a substantial transfer improvement: it produces fewer extra
objects, misses fewer baseline objects, increases matched coverage, and
greatly improves temporal-symmetry agreement. This is not universal success.
Subjects 5, 35, 38, and 39 remain severe failures under the frozen tolerance;
subject 39 has no matched LLM-baseline objects. The fixed envelope therefore
improves the current construction but does not establish detector equivalence
across all subjects.

## Reproduction

```bash
python experiments/bidmc_llm_capture/multi_subject_comparison.py \
  --subjects 1-53 \
  --construction envelope \
  --output-directory \
  experiments/bidmc_llm_capture/results/envelope_multi_subject
```

Exact object, annotation, subject, and cohort tables are stored in
`results/envelope_multi_subject/`.
