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
