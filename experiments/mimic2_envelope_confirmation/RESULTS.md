# Untouched-cohort confirmation results

Run completed August 17, 2026 from Git revision
`0ea57bb75c1c42431c2375888b3381a74571d80f`.

## Cohort

The deterministic scan considered 124 non-BIDMC MIMIC-II source subjects in
lexicographic order before obtaining the first 20 eligible subjects. The 53
subjects used by the curated BIDMC dataset were excluded before scanning. One
candidate source subject, `s01033`, had WFDB invalid samples in its first
window and was excluded under the frozen signal-validity criterion. No window
was selected or excluded using detector output or visual waveform inspection.

The selected cohort contains 20 distinct subjects and 20 unique eight-minute
RESP windows, totaling approximately 160 minutes. Subject `s00672` produced no
objects under either FeatureGraph construction or the frozen SciPy comparator;
it remains in all summaries.

## Prospectively declared criteria

All four criteria declared in `PROTOCOL.md` passed.

| Criterion | Result |
| --- | --- |
| Preserve FeatureGraph detected-peak count in every window | Passed; 3,811 versus 3,811 |
| Do not decrease cohort-wide matched objects | Passed; 2,792 to 2,859 |
| Do not increase SciPy-only objects | Passed; 149 to 82 |
| Reduce median absolute matched-peak error | Passed; 17 to 7 samples |

## Cohort results

| Measure | Envelope leading edge | Plateau midpoint | Delta |
| --- | ---: | ---: | ---: |
| Detected FeatureGraph peak events | 3,811 | 3,811 | 0 |
| Complete FeatureGraph objects | 3,802 | 3,773 | -29 |
| Complete SciPy objects | 2,941 | 2,941 | 0 |
| Matched objects | 2,792 | 2,859 | +67 |
| FeatureGraph-only objects | 1,010 | 914 | -96 |
| SciPy-only objects | 149 | 82 | -67 |
| Aggregate FeatureGraph matched fraction | 73.4% | 75.8% | +2.4 points |
| Aggregate SciPy matched fraction | 94.9% | 97.2% | +2.3 points |
| Median subject FeatureGraph matched fraction | 70.5% | 72.2% | +1.7 points |
| Median subject SciPy matched fraction | 96.2% | 98.7% | +2.5 points |
| Median absolute peak error | 17 samples | 7 samples | -10 samples |
| 90th-percentile absolute peak error | 50 samples | 24 samples | -26 samples |
| Median absolute period error | 0.088 s | 0.056 s | -0.032 s |
| Median absolute full-excursion error | 0 | 0 | 0 |
| Median absolute temporal-symmetry error | 0.0922 | 0.0531 | -0.0391 |
| Ambiguous FeatureGraph objects | 0 | 48 | +48 explicitly represented |
| Formerly complete objects invalidated by ambiguity | 0 | 29 | +29 explicitly excluded |

Matches increased on 13 subjects and were unchanged on seven; they did not
decrease on any subject. SciPy-only counts decreased on the same 13 subjects
and were unchanged on seven. FeatureGraph-only counts decreased on 18 subjects
and were unchanged on two. Among the 19 subjects with matched peaks, median
peak error decreased on 16 and was unchanged on three.

## Interpretation

This prospective result confirms the representation correction observed in
the 53 curated BIDMC records. Exact-flat extrema are better represented as
intervals whose midpoint can be projected for comparison with point-based
detectors. The projection improves object alignment and boundary-sensitive
measurements without adding or deleting detected peak events.

It does not confirm detector equivalence or clinical breath validity. The
plateau construction still produced 914 complete FeatureGraph objects without
a matched SciPy object, while SciPy produced 82 without a matched FeatureGraph
object. The source windows have no independent manual breath annotations.
These results therefore confirm transfer of the interval-to-point
representation correction, not the physiological meaning of every candidate
cycle.

## Reproducibility

- Runner SHA-256:
  `f5f8060f5e5a57fba90e341ffee6352c629db7889757c884a384ffde88dc2282`
- Protocol SHA-256:
  `352dc7c58c67df2db11623090a1197a6366212f8e4c90e25d7bc0bbe87525a47`
- Machine-readable decision: `results/mimic2_envelope_confirmation/confirmation_decision.json`
- Cohort and object tables: `results/mimic2_envelope_confirmation/`
