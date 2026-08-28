# 1. Introduction

**Research question:** When different rolling-envelope parameter sets cause the same construction to produce different respiratory-waveform objects, how can the differences be made explicit, and what can their relationships to independent physiological signals reveal about the structure being represented?

Time-series studies often reduce agreement between two computational methods to a single summary score. This makes it difficult to locate individual disagreements, determine how they arise, or test whether discordant events form a homogeneous error category. Respiratory waveforms contain structure at multiple temporal scales, and changing the temporal scale of a representation can alter which signal reversals are preserved and which apparent breaths are constructed.

Even within a single deterministic construction, changing one temporal-scale parameter can produce different boundaries and object identities. These unmatched objects do not necessarily represent errors. They may in fact reveal organized signal structure that was not preserved at a different temporal scale.

[FeatureGraph](https://github.com/featuregraph/featuregraph) is a deterministic representation framework for constructing explicit behavioral objects from ordered observations. In this study, we used it to classify respiratory-waveform samples as rising, falling, or inactive and to mark the boundaries at which these states began and ended. Ordered state transitions were then composed into explicit trough–peak–trough waveform objects.

It is crucial that while many parts of the data-analysis process can be automated, the software should execute rather than determine the scientific rules of the analysis. The researcher specifies the representation, validation, and comparison rules; FeatureGraph applies those rules deterministically; and the scientific meaning of the resulting objects remains a matter for investigation. Preserving those roles makes it possible to report which decisions were made by the researcher, which operations were automated by the software, and which scientific interpretations were supported by the resulting evidence.

Using researcher-specified rules, FeatureGraph converted each respiratory waveform into representational records at rolling-envelope scales of 79 and 100 samples. Four development records were used to inspect the behavior of both scales and define the waveform-construction, cross-scale-matching, ECG-validation, cardiac-phase, annotation-comparison, and eligibility rules. We then froze the [complete analysis contract](https://github.com/featuregraph/featuregraph/blob/main/artifacts/studies/bidmc_multiscale_contract.md) before evaluating the remaining 49 records. Finally, we investigated whether objects introduced at the shorter temporal scale exhibited organized physiological structure, using respiratory, ECG, and breath-annotation signals from the BIDMC dataset.

The contributions of this study are:

1. An explicit, researcher-authored contract specifying respiratory-waveform construction, cross-scale matching, ECG validation, cardiac-phase calculation, annotation comparison, eligibility requirements, and claim boundaries.
2. A reproducible workflow that applies the same frozen construction and analysis rules independently to every record.
3. An inspectable population of respiratory-waveform objects constructed at the shorter temporal scale but not matched to objects constructed at the longer scale.
4. [Held-out evidence](https://github.com/featuregraph/featuregraph/blob/main/artifacts/studies/bidmc_multiscale_heldout/report.md) that, in a substantial subset of eligible records, shorter-scale-only objects are more concentrated within the cardiac cycle than objects shared across both scales.

# 2. Dataset and signals

The study uses all 53 eight-minute recordings in the publicly available [BIDMC PPG and Respiration Dataset](https://physionet.org/content/bidmc/1.0.0/). Each record contains simultaneously acquired impedance-pneumography respiratory, electrocardiographic (ECG), and photoplethysmographic signals sampled at 125 Hz. It also contains physiological monitor measurements, including heart rate and respiratory rate, sampled at 1 Hz, together with breath annotations supplied independently by two annotators.

The recordings were obtained from critically ill patients in the medical and surgical intensive care units of Beth Israel Deaconess Medical Center in Boston, Massachusetts. The BIDMC dataset was first reported by Pimentel et al. in *[Towards a Robust Estimation of Respiratory Rate from Pulse Oximeters](https://doi.org/10.1109/TBME.2016.2613124)*.

# 3. Respiratory waveform construction

The researcher input declares the 53-record BIDMC cohort, the raw respiration signal, and two rolling-envelope parameterizations at 79 and 100 samples. The two window lengths were treated as estimated temporal scales rather than optimal breath-detection parameters. Because a rolling maximum followed by a rolling mean has an effective support of (2W-1) samples, the 79- and 100-sample parameterizations correspond to effective supports of 157 and 199 samples, or approximately 1.256 and 1.592 seconds at 125 Hz. These scales specify shorter- and longer-scale constructions for comparison; we did not assume in advance which waveform structures either construction would preserve or what physiological processes those structures would represent.

For the first construction, the rolling envelope was set at 79 samples and consisted of a rolling maximum followed by a rolling mean and offline alignment of the rolling-envelope waveform to the input waveform. The process was repeated for the 100-sample construction. The resulting object populations could therefore differ because changing the rolling-window length altered which waveform reversals were preserved.

Because these rolling operations were computed offline rather than causally, the resulting envelope was aligned with the original waveform to correct for the temporal displacement introduced by the rolling windows. The alignment rule was applied identically at both scales and was not fitted separately to individual records. Directional changes in each aligned envelope were used to classify states as rising, falling, or inactive. Boundaries marked the entry into and exit from each state, and ordered state transitions were composed into complete trough–peak–trough objects.

# 4. Cross-scale object comparison

Objects were classified according to whether they could be matched across the two temporal scales. scales. Shared objects were constructed at both the 79 and 100-sample level, whereas shorter-scale or longer-scale objects were constructed at the shorter and longer scales respectively. Across all 53 records, 

- 7918 objects were matched across the two temporal scales and classified as shared.
- An additional 862 objects were constructed only at 79 samples, while 8 objects were constructed only at 100 samples.
- Thus, the shorter-scale construction produced 8780 objects in total, compared with 7926 at the longer scale.
