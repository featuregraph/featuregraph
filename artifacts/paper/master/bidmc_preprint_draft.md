# 1. Introduction

**Research question:** When different rolling-envelope parameter sets cause the same construction to produce different respiratory-waveform objects, how can those differences be made explicit, and what can their relationships to independently recorded signals reveal about the represented structure?

Time-series studies often reduce agreement between two computational methods to a single summary score. This makes it difficult to locate individual disagreements, determine how they arise, or test whether discordant events form a homogeneous error category. A waveform can contain structure at multiple temporal scales, and changing the scale of its representation can alter which reversals are preserved and which objects are constructed.

Even within a single deterministic construction, changing one temporal-scale parameter can produce different boundaries and object identities. The resulting unmatched objects do not necessarily represent errors. They may expose organized signal structure that is not preserved at another temporal scale.

[FeatureGraph](https://github.com/featuregraph/featuregraph) is a deterministic representation framework for constructing explicit behavioral objects from ordered observations. In this study, we used it to classify respiratory-waveform samples as rising, falling, or inactive and to mark the boundaries at which those states began and ended. Ordered state transitions were then composed into explicit trough–peak–trough waveform objects.

Although many parts of data analysis can be automated, the software should execute rather than determine the scientific rules of the analysis. The researcher specifies the representation, validation, and comparison rules; FeatureGraph applies those rules deterministically; and the meaning of the resulting objects remains a matter for investigation. Preserving these roles makes it possible to report which decisions were made by the researcher, which operations were automated by the software, and which interpretations were supported by the resulting evidence.

Using researcher-specified rules, FeatureGraph converted each respiratory waveform into representational records at rolling-envelope scales of 79 and 100 samples. Four development records were used to inspect the behavior of both scales and define the waveform-construction, cross-scale-matching, ECG-validation, event-phase, annotation-comparison, and eligibility rules. We then froze the [complete analysis contract](https://github.com/featuregraph/featuregraph/blob/main/artifacts/studies/bidmc_multiscale_contract.md) before evaluating the remaining 49 records. Finally, we tested whether objects introduced at the shorter temporal scale had a consistent relationship to events in the independently recorded ECG signal.

The contributions of this study are:

1. An explicit, researcher-authored contract specifying respiratory-waveform construction, cross-scale matching, ECG validation, event-phase calculation, annotation comparison, eligibility requirements, and claim boundaries.
2. A reproducible workflow that applies the same frozen construction and analysis rules independently to every record.
3. An inspectable population of respiratory-waveform objects constructed at the shorter temporal scale but not matched to objects constructed at the longer scale.
4. [Held-out evidence](https://github.com/featuregraph/featuregraph/blob/main/artifacts/studies/bidmc_multiscale_heldout/report.md) that, in a substantial subset of eligible records, shorter-scale-only objects occur at more consistent positions between successive ECG events than objects shared across both scales.

# 2. Dataset and signals

The study uses all 53 eight-minute recordings in the publicly available [BIDMC PPG and Respiration Dataset](https://physionet.org/content/bidmc/1.0.0/). Each record contains simultaneously acquired impedance-pneumography respiratory, electrocardiographic (ECG), and photoplethysmographic signals sampled at 125 Hz. It also contains monitor measurements, including heart rate and respiratory rate, sampled at 1 Hz, together with breath annotations supplied independently by two annotators.

The respiratory waveform served as the input to the object construction. ECG lead II, secondary ECG leads V and AVR when available, and monitor heart rate served as validation and comparison data. The two breath-annotation series provided an additional comparison and were not treated as definitive labels for the constructed objects.

The recordings were obtained from patients in the medical and surgical intensive care units of Beth Israel Deaconess Medical Center in Boston, Massachusetts. The BIDMC dataset was first reported by Pimentel et al. in *[Towards a Robust Estimation of Respiratory Rate from Pulse Oximeters](https://doi.org/10.1109/TBME.2016.2613124)*.

# 3. Respiratory-waveform construction

The researcher input declares the 53-record BIDMC cohort, the raw impedance respiratory signal, and two rolling-envelope parameterizations at 79 and 100 samples. The two window lengths were treated as estimated temporal scales rather than optimal detection parameters. Because a rolling maximum followed by a rolling mean has an effective support of \(2W-1\) samples, the 79- and 100-sample parameterizations correspond to effective supports of 157 and 199 samples, or approximately 1.256 and 1.592 seconds at 125 Hz. We did not assume in advance which waveform structures either scale would preserve.

For each parameterization, the rolling envelope consisted of a rolling maximum followed by a rolling mean and offline alignment of the resulting waveform to the input waveform. The same alignment rule was applied at both scales and across all records. Window length was the only construction parameter that differed.

Directional changes in each aligned envelope were used to classify states as rising when the first difference exceeded \(10^{-12}\), falling when it was less than \(-10^{-12}\), and inactive when its absolute value was at most \(10^{-12}\). Boundaries marked entry into and exit from each state, and ordered state transitions were composed into trough–peak–trough objects. A complete object required an ordered start trough, peak, and end trough with nonoverlapping boundary intervals; partial objects at the rolling-window edges, the final open object, and objects with ambiguous plateau ordering were excluded.

# 4. Cross-scale object comparison

Objects were classified according to whether they could be matched across the two temporal scales. Shared objects were constructed at both the 79- and 100-sample scales, whereas shorter-scale-only and longer-scale-only objects were constructed exclusively at 79 and 100 samples, respectively. Complete objects were matched by peak index using a tolerance of 63 samples, equivalent to 0.504 seconds at 125 Hz.

The ordered one-to-one procedure first maximized the number of matches and then minimized the total absolute difference between matched peak indices while preserving temporal order. A matched pair was classified as shared even when its start, peak, or end boundaries differed, so both boundary sets remained available for comparison. When one longer-scale object corresponded to several shorter-scale objects, at most one pair was matched and the remaining shorter-scale objects were retained as shorter-scale-only objects. Unmatched objects were retained as comparison populations and were not classified as errors.

Across all 53 records:

- 7,918 objects were matched across the two temporal scales and classified as shared.
- 862 objects were constructed only at 79 samples.
- 8 objects were constructed only at 100 samples.
- The shorter-scale construction produced 8,780 objects in total, compared with 7,926 at the longer scale.

# 5. Development and held-out design

The development set consisted of records 13, 19, 23, and 33; the remaining 49 records formed the held-out set. In the development records, some objects introduced by the 79-sample construction occurred at consistent positions between successive ECG events. These observations were used to define the object-matching, ECG-validation, event-phase, annotation-comparison, and eligibility rules.

The contract was frozen before those rules were applied unchanged to the 49 held-out records. The first held-out run stopped because at least one record did not contain the expected AVR column. The schema-handling logic was corrected so that validation used lead V when AVR was unavailable; lead II remained the primary ECG event series in every record. No scientific or analytical parameter was changed.

# 6. ECG-event construction and validation

ECG events were used as an independent timestamp series against which the respiratory-waveform object peaks could be positioned. Events detected from ECG lead II were checked against the available secondary ECG leads and the dataset's monitor heart-rate values using rules fixed during development. The complete event-detection and validation parameters are reported in the [frozen analysis contract](https://github.com/featuregraph/featuregraph/blob/main/artifacts/studies/bidmc_multiscale_contract.md) and reproduction code.

Forty-one of the 49 held-out records passed the validation requirements. The other eight records were excluded from the ECG-relative analysis because they did not meet one or more prespecified checks: agreement between ECG leads, the event detector's supported rate range, or agreement between the event count and monitor heart rate. These exclusions remained visible in the published coverage table rather than being removed or corrected through record-specific parameter changes.

# 7. Cardiac-phase calculation

Every respiratory-object peak bracketed by two consecutive lead-II R events was
assigned a position within that cardiac cycle:

\[ \text{phase} = \frac{\text{respiratory peak} - \text{preceding } R}{\text{following } R - \text{preceding } R} \]

The result is a value in [0, 1). Peaks not bracketed by two events, including
those before the first and after the last detected event, contributed no phase.

Phase is circular, so we summarised a set of phases by the resultant length of
their unit vectors. The resultant length runs from zero, when phases are spread
uniformly around the cycle, to one, when every object occupies the identical
cardiac phase. It is a measure of concentration and carries no information
about where in the cycle that concentration sits.

We calculated the resultant length separately for shared objects and for
W=79-only objects within each ECG-valid record. A class-specific estimate
required at least five eligible objects of that class in that record. Records
supplying fewer than five objects in either class contributed no difference and
are reported in the coverage table rather than dropped.

# 8. Annotation relationship

The BIDMC dataset supplies two independent breath-annotation series. A W=79-only
peak was recorded as annotation-supported when either series contained an event
within 63 samples, the same tolerance used for cross-scale matching.

This is a relationship, not a truth label. The two series disagree with each
other in regions where shorter-scale objects occur, and one annotator marked a
W=79-only peak that the other did not. Proximity to an annotation therefore does
not establish the physiological identity of an object, and the absence of a
nearby annotation does not establish that an object is spurious. We report the
fraction and draw no inference from it about which objects are breaths.

# 9. Frozen outcomes and claim boundaries

The primary held-out outcome was fixed before execution as the subject-level
difference between class concentrations:

\[ \Delta R = R(\text{W=79-only}) - R(\text{shared}) \]

We report its distribution and the number of subjects for which it is positive.
Secondary outcomes are W=79-only counts and concentration by subject, the
annotation-supported fraction, and ECG-valid coverage with every exclusion
reason. No parameter was tuned from the held-out result.

The analysis tests one thing: whether objects introduced by the shorter temporal
scale occupy more consistent positions in the cardiac cycle than objects shared
by both scales. It does not assume that every W=79-only object is cardiogenic,
that every shared object is a validated breath, or that phase concentration
establishes a physiological mechanism. A positive difference is evidence that
the two populations differ in their relationship to an independently recorded
signal. It is not evidence of what either population is.

# 10. Results

## 10.1 Coverage and exclusions

Forty-one of the 49 held-out records met every prespecified ECG gate. Eight did
not, and remain in the coverage table:

| Exclusion reason | Records |
| --- | ---: |
| Cross-lead agreement below 0.90 | 4 |
| Monitor rate outside the refractory contract, derived-monitor difference above 5 beats/min, and cross-lead agreement below 0.90 | 2 |
| Derived-monitor heart-rate difference above 5 beats/min | 1 |
| Monitor rate outside the refractory contract | 1 |

No alternative lead or parameter was substituted for an excluded record.

## 10.2 Object populations

Across all 53 records, the shorter scale constructed 8,780 complete objects and
the longer scale 7,926. Matching produced 7,918 shared objects, 862 objects
constructed only at W=79, and 8 constructed only at W=100. Shortening the window
therefore added objects and almost never removed them: the two representations
are close to nested, which is what makes the W=79-only population a coherent
class rather than a mixture of gains and losses.

Within the 49 held-out records the same construction produced 7,584 W=79 objects,
7,192 W=100 objects, 7,186 shared, and 398 W=79-only. Restricting to the 41
ECG-valid records leaves 6,407 W=79 objects, 6,074 shared, and 333 W=79-only.

The four development records contributed 464 of the corpus total of 862
W=79-only objects, and subject 13 alone contributed 194. The development set is
therefore unusually rich in the phenomenon the contract was written to examine,
which is a consequence of how those records were selected and a reason the
held-out evaluation is the load-bearing one.

## 10.3 Eligibility

Of the 41 ECG-valid held-out records, 8 produced no W=79-only objects at all and
13 produced between one and four, below the five required for a class-specific
concentration estimate. Twenty records supplied at least five in both classes and
yielded a difference. The primary outcome is therefore estimated on 20 of 49
held-out records, and the 21 ECG-valid records that produced too few W=79-only
objects are themselves a result: at most scales the shorter window adds nothing.

## 10.4 Primary outcome

Across the 20 eligible records the median difference in phase concentration was
0.269, and 14 of the 20 differences were positive. The distribution is wide:
the interquartile range runs from −0.038 to 0.459 and the full range from −0.287
to 0.827.

Median concentration was 0.382 for shared objects and 0.579 for W=79-only
objects. Six records showed the opposite ordering.

The result is descriptive. It says that in a majority of eligible held-out
records, objects introduced by the shorter scale sit at more consistent cardiac
phases than objects both scales agree on, and that the effect is not uniform.

## 10.5 Annotation relationship

Twenty-nine of the 333 W=79-only objects in ECG-valid held-out records, or 8.7%,
had an event in either annotation series within 63 samples. Across all 49
held-out records the count was 38 of 398.

Most W=79-only objects are not near an annotated breath. Under the claim
boundaries in Section 9 this neither confirms nor refutes a cardiogenic reading:
the annotation series were not constructed to mark cardiac-frequency structure,
and they disagree with each other where such structure occurs.
