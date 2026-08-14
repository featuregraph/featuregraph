# Frozen BIDMC multi-subject transfer record

## Purpose

This phase tests whether the subject 1 constructions transfer without further
LLM access or subject-specific tuning. It is not a series of 52 newly tuned
LLM analyses. The two frozen paths are:

1. native FeatureGraph with no smoothing, `diff_lag=45`, `eps=0.15`, and
   `max_state_gap=7`; and
2. the fully recorded method selected by the blinded subject 1 LLM run: a
   fourth-order 0.8 Hz Butterworth filter followed by SciPy `find_peaks` on the
   filtered signal and its negation, with distance 188 and prominence 0.08.

Both paths use the same complete-object and measurement contracts. Complete
objects are matched one-to-one in temporal order within 63 samples, maximizing
the number of matches and then minimizing total peak error. Neither detector
uses the BIDMC annotations to construct or modify objects.

The evaluation covers all 53 BIDMC subjects. Subject 1 remains the development
record; subjects 2–53 form the frozen transfer cohort.

## Main result

The subject 1 agreement does not transfer uniformly. Across the 52 held-out
subjects, FeatureGraph returns 8,786 complete objects and the recorded
LLM-selected baseline returns 6,999. Of these, 6,031 match. This is 68.6% of
FeatureGraph objects and 86.2% of baseline objects. The median subject-level
matched fractions are 78.5% and 99.1%, respectively, showing that the baseline
is often nearly a subset of FeatureGraph even though several records exhibit
large failures in the opposite direction.

| Frozen transfer measure, subjects 2–53 | Result |
| --- | ---: |
| FeatureGraph complete objects | 8,786 |
| LLM-selected baseline complete objects | 6,999 |
| Matched objects | 6,031 |
| FeatureGraph-only objects | 2,755 |
| Baseline-only objects | 968 |
| FeatureGraph matched fraction | 68.6% |
| Baseline matched fraction | 86.2% |
| Subjects with no baseline-only objects | 20 of 52 |
| Subjects with at least 90% matched in both directions | 12 of 52 |

This is a transfer failure of the frozen native detector, not a failure of
FeatureGraph's deterministic execution. The explicit construction runs on
every record and exposes exactly where its fixed rule produces too many or too
few objects. The absolute `diff(45) > 0.15` state definition is not invariant
to subject-level waveform scale, rise rate, morphology, or noise.

## Boundary and property agreement

For the 6,031 matched held-out objects, peak placement remains comparatively
close: median absolute error is 12 samples (0.096 seconds), the 90th percentile
is 34 samples (0.272 seconds), and every matched pair is within the declared
63-sample tolerance. Trough-derived boundaries remain systematically later in
FeatureGraph: median signed start and end differences are +85 and +71 samples.

| Matched-object measure, subjects 2–53 | Median absolute error | 90th percentile |
| --- | ---: | ---: |
| Peak index | 12 samples | 34 samples |
| Period | 0.088 s | 2.760 s |
| Full excursion | 0.000 | 0.0685 |
| Temporal symmetry | 0.357 | 0.641 |

The small median period error coexists with a long error tail. When one path
splits or omits intervening objects, peak-to-peak periods no longer describe
the same adjacency relation even when a later peak can still be matched. Full
excursion is robust for most matched intervals because the overlapping raw
intervals often contain the same extrema. Symmetry remains systematically
lower for FeatureGraph: matched means are 0.438 and 0.814, reflecting the
different trough semantics already seen in subject 1.

## Annotation check

The two BIDMC breath-annotation columns were used only after construction.
Across subjects 2–53, the frozen LLM-selected baseline matches 95.2% and 97.3%
of annotated breaths. FeatureGraph matches 83.0% and 84.3%. In the other
direction, 91.9% and 95.1% of baseline peaks match annotations, compared with
66.9% and 68.9% of FeatureGraph peaks.

| Subjects 2–53 | Ann1 reference matched | Ann2 reference matched | Ann1 detected matched | Ann2 detected matched |
| --- | ---: | ---: | ---: | ---: |
| Native FeatureGraph | 83.0% | 84.3% | 66.9% | 68.9% |
| LLM-selected baseline | 95.2% | 97.3% | 91.9% | 95.1% |

Of the 2,755 FeatureGraph-only complete objects, 2,342 (85.0%) are excluded by
both annotators under the frozen matching rule. This supports the diagnosis of
native over-segmentation on many records. It is not the only failure: some
subjects show severe native under-detection, including subjects 5, 13, 19, 27,
and 45. Thus no single "extra secondary rise" description covers the entire
cohort.

Exact peak identity inside a tolerance neighborhood can depend on the matching
objective when multiple native candidates surround one annotation. Subject 1
therefore supports agreement on five excess candidate neighborhoods, but the
earlier claim that both annotators exclude the exact same five peak indices is
too strong. The stored optimal ordered matches make this ambiguity explicit.

## Interpretation for the research question

The experiment demonstrates three different capabilities:

- **Preservation:** the LLM-selected baseline was recorded completely and now
  runs over all subjects without an LLM.
- **Auditability:** FeatureGraph's states, boundaries, incomplete objects, and
  failures remain inspectable on every subject.
- **Transfer:** the current native parameterization is not sufficiently
  transferable. Determinism preserves a rule; it does not make a
  subject-specific rule general.

This is more informative than presenting subject 1 alone as evidence of broad
equivalence. It identifies the next research problem precisely: replace the
absolute subject-specific state threshold with a documented scale-adaptive or
otherwise transferable transition contract, select that contract on a
declared development subset, and evaluate it once on a held-out subset. That
future detector must not be tuned separately for each evaluation subject.

## Reproduction

Run:

```bash
PYTHONPATH=. python experiments/bidmc_llm_capture/multi_subject_comparison.py \
  --subjects 1-53 --jobs 4
```

The command downloads the public BIDMC signal and breath files through the
FeatureGraph dataset loader and writes the subject summary, all matched and
unmatched object rows, annotation summaries, and unmatched annotation peaks to
`results/multi_subject/`.
