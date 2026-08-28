Introduction

Research question: when different rolling-envelope parameter sets cause the same construction to produce different respiratory-waveform objects, how can the differences be made explicit, and what can their relationships to independent physiological signals reveal about the structure being represented?

Time-series studies often reduce agreement between two computational methods to a single summary score. This makes it difficult to locate individual disagreements, determine how they arise, or test whether discordant events form a homogeneous error category. Respiratory waveforms contain structure at multiple temporal scales, and changing the temporal scale of a representation can alter which signal reversals are preserved and which apparent breaths are constructed.

Even within a single deterministic construction, changing one temporal-scale parameter can produce different boundaries and object identities. These unmatched objects do not necessarily represent errors. They may in fact reveal organized signal structure that was not preserved at a different temporal scale.

FeatureGraph is a deterministic representation framework for constructing explicit behavioral objects from ordered observations. In this study, we used it to classify respiratory-waveform samples as rising, falling, or inactive and to mark the boundaries at which these states began and ended. Ordered state transitions were then composed into explicit trough-peak-trough waveform objects.

It is crucial that while many parts of the data analysis process can be automated, the software should execute rather than determine the scientific rules of the analysis. The researcher specifies the representation, validation, and comparison rules, FeatureGraph applies those rules deterministically, and the scientific meaning of the resulting objects remains a matter for investigation. Preserving those roles makes it possible to report which decisions were made by the researcher, what was automated by the software, and what scientific interpretations were supported by the resulting evidence.

Using researcher-specified protocols, FeatureGraph converted each respiratory waveform into representational records at rolling-envelope scales of 79 and 100 samples. Four development records were used to inspect the behavior of both scales and define the waveform-construction, cross-scale matching, ECG-validation, cardiac-phase, annotation-comparison, and eligibility rules. We then froze the complete analysis contract before evaluating the remaining 49 records. Finally, we investigated whether objects introduced at the shorter temporal scale exhibited organized physiological structure, using respiratory, ECG, and breath-annotation signals from the BIDMC dataset. 

The contributions of this study are:

An explicit researcher-authored contract for a respiratory waveform-construction, cross-scale matching, ECG-validation, cardiac-phase, annotation-comparison, and eligibility rules.
A reproducible workflow that executes the frozen construction independently across all records.
An inspectable population of objects introduced by the shorter temporal scale but not matched to objects constructed at the longer scale.
Held-out evidence that this population is often more cardiac-phase concentrated than object shared across scales.

Dataset and signals
The study uses all 53 eight-minute recordings in the public BIDMC dataset (link). Each record contain simultaneously acquired impedance-pneumography respiratory, electrocardiographic (ECG), and photoplethysmographic signals sampled at 125 Hz. It also contains physiological monitor measurements, including heart rate and respiratory rate, sampled at 1 Hz, together with breath annotations supplied independently by two annotators. 

The recordings were obtained from critically ill patients at the medical and surgical intensive care units of Beth Israel Deaconess Medical Center in Boston, Massachusetts. The BIDMC dataset was first reported by Pimentel et al. in Towards a Robust Estimation of Respiratory Rate from Pulse Oximeters (DOI: 10.1109/TBME.2016.2613124).

Respiratory waveform construction

The researcher input declares the 53-record BIDMC cohort, the raw respiration signal, and the two rolling-envelope parameterizations at 79 and 100 samples. The 79-sample window was selected during exploratory analysis from the dataset's sampling frequency of 125 Hz. A target temporal support of 0.625 seconds, representing half of a 1.25-second respiratory cycle, corresponds to 78.125 samples, which we rounded up to 79, giving an implemented window duration of 0.632 seconds.

For the first construction, the rolling envelope is set at 79 samples, consisting of a rolling-maximum followed by a rolling-mean and offline alignment of the rolling-envelope waveform to the input waveform. The process is repeated for the 100-sample construction. The resulting object populations could therefore differ because changing the rolling-window length altered which waveform reversals were preserved.

Because these rolling operations were computed offline rather than causally, the resulting envelope was aligned with the original waveform to correct for the temporal displacement introduced by the rolling windows. The alignment rule was applied identically at both scales and was not fitted separately to individual records. Directional changes in each aligned envelope were used to classify states as rising, falling, or inactive. Boundaries marked the entry into and exit from each state, and ordered state transitions were composed into complete trough-peak-trough objects. 



