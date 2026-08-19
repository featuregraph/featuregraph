## Evaluation methods

The alpha implementation was evaluated using synthetic oscillatory signals for which the number, locations, boundaries, and properties of the underlying oscillations were known analytically. The evaluation had three purposes. First, it tested whether FeatureGraph could recover a noise-free construction exactly when its state definition was aligned with the generating process. Second, it measured detection, localization, and property error under increasing additive noise. Third, it examined how the construction changed as its smoothing, difference-lag, and tolerance parameters changed. SciPy peak detection was included as a conventional detection baseline. The comparison was intended to characterize the behavior and limitations of the alpha construction, not to establish FeatureGraph as a universally superior oscillation detector.

All reported experiments used FeatureGraph `v0.1.0a1` at source commit `1e585a76e3e2c19c05a1b9711319eb48317f5e37`. The archived run used Python 3.12.13, NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0, and Matplotlib 3.10.8 on Linux. The complete parameter specification, random seeds, tables, figures, software versions, and SHA-256 hashes of the generated artifacts were recorded in the evaluation manifest.

### Synthetic signals and ground truth

Each evaluation signal contained 12 complete sinusoidal oscillations with a period of 80 samples, an amplitude of one, and a baseline of zero. The clean signal was generated as \(x_i=-\cos(2\pi i/80)\). A further half-cycle of right-edge context was retained so that the closing trough of the twelfth evaluated object remained observable under every tested difference lag; this context was not counted as an additional ground-truth object. Every evaluated object therefore had a known start trough, peak, and end trough. For the robustness experiments, independent zero-mean Gaussian noise was added to the clean signal. Noise standard deviations were 0, 0.05, 0.10, 0.20, 0.30, and 0.40 relative to the unit signal amplitude.

The ground-truth object table was generated from the known extrema rather than estimated from the noisy observations. Each true oscillation therefore had an exact start index, peak index, end index, duration, amplitude, and temporal symmetry. This table supplied a common reference for both FeatureGraph and the SciPy baseline.

### Exact-recovery check

Before parameter tuning, FeatureGraph was applied to the clean synthetic sequence using a construction that preserved the sample-level reversals of the generating sinusoid. The resulting object table was compared directly with the analytical ground truth. This check required equality of the detected and true object counts and evaluated start, peak, and end localization together with duration, amplitude, and temporal symmetry. Its purpose was to verify the internal construction and measurement pipeline under an ideal condition; it was not used to select the operating point for the noise experiment.

The treatment of incomplete objects and group boundaries was also checked independently using two six-cycle sequences with different phase offsets. For each sequence, the total number of constructed identifiers and the numbers classified as complete and partial were recorded. This diagnostic tested the structural completeness rule separately from oscillation detection accuracy and verified that objects were constructed independently within each sequence.

### FeatureGraph operating-point selection

FeatureGraph was evaluated with smoothing enabled. Three parameters were varied: smoothing-window length, difference lag, and epsilon. The grid contained smoothing windows of 1, 5, 9, and 15 samples; difference lags of 1, 3, 5, and 10 samples; and epsilon values of 0, 0.01, and 0.03. This produced 48 parameter combinations.

Parameter selection used 20 independently generated noisy signals at a fixed noise standard deviation of 0.20. The tuning seeds were 1729 through 1748. Each parameter combination was applied to every tuning replicate, and object-level F1 was averaged across the 20 signals. The combination with the highest mean F1 was selected before evaluation on the held-out test seeds. The selected FeatureGraph operating point used a smoothing window of 9 samples, a difference lag of 10 samples, and epsilon equal to 0.03.

This procedure selected a single operating point for all test noise levels. Parameters were not retuned separately at each noise level. The full tuning table was retained to expose parameter sensitivity rather than reporting only the selected combination.

### SciPy baseline

The baseline used SciPy peak finding to identify positive peaks and corresponding trough boundaries. Its grid varied minimum peak distance as a fraction of the known 80-sample period and varied prominence. Distance fractions were 0.30, 0.45, and 0.60, and prominence values were 0.10, 0.25, and 0.40, producing nine combinations. The distance fraction was converted to a minimum separation in samples.

The SciPy grid was tuned on the same 20 noisy signals at noise standard deviation 0.20 and selected by mean object-level F1. The chosen baseline used a distance fraction of 0.60 and a prominence of 0.10. As with FeatureGraph, this operating point was fixed before held-out testing and was used unchanged at every test noise level.

SciPy supplied detected extrema rather than a FeatureGraph behavioral record. For comparability, its detected peaks and surrounding troughs were assembled into trough–peak–trough intervals, and the same boundary and property measures were calculated for those intervals. The baseline therefore evaluated whether a conventional detector could recover the same synthetic objects, while FeatureGraph additionally retained the sample-level states, events, identifiers, construction parameters, and queryable object representation described in the preceding sections.

### Object matching

Detected and true objects were matched one to one using both landmark and interval agreement. A candidate match required the detected peak to fall within 10 samples of the true peak and the intersection-over-union (IoU) of the detected and true trough-to-trough intervals to be at least 0.50. For intervals (D) and (T), IoU was defined as

\[
\operatorname{IoU}(D,T)
=
\frac{|D \cap T|}{|D \cup T|}.
\]

Once an object had been matched, it could not be assigned to another object. Unmatched detections were counted as false positives, and unmatched ground-truth objects were counted as false negatives. Requiring both a nearby peak and adequate interval overlap prevented a detection from being credited solely because one landmark happened to be close to a true peak.

### Detection, localization, and property metrics

For each signal, object-level precision, recall, and F1 were calculated from the numbers of matched objects, detections, and true objects:

\[
\mathrm{precision} = \frac{TP}{TP+FP},
\qquad
\mathrm{recall} = \frac{TP}{TP+FN},
\]

\[
F_1 =
2\frac{\mathrm{precision}\,\mathrm{recall}}
{\mathrm{precision}+\mathrm{recall}}.
\]

Interval agreement was summarized as mean IoU over matched objects. Landmark localization was measured using mean absolute error (MAE) in samples for the start, peak, and end indices. Duration MAE was calculated from detected and true trough-to-trough durations. Amplitude MAE and temporal-symmetry MAE measured error in the corresponding object properties. Property and localization errors were evaluated only for matched objects; an unmatched object contributed to detection error rather than receiving an arbitrary property error.

### Held-out robustness evaluation

The fixed operating points were evaluated on 30 previously unused random seeds, 11729 through 11758, at each of the six noise levels. The same underlying 12-cycle construction and the same set of test seeds were used for both methods. In total, each method was evaluated on 180 held-out noisy signals and 2,160 ground-truth oscillations across the complete noise series.

Metrics were first calculated separately for each signal. For each method and noise level, the reported mean and standard deviation were then calculated across the 30 replicates. The reported 95% uncertainty half-width for F1 was the normal-approximation standard error interval

\[
h_{0.95} = 1.96\frac{s}{\sqrt{n}},
\]

where (s) was the sample standard deviation of replicate-level F1 and (n=30). The tuning tables used the same calculation with (n=20). The interval was used to describe variability across generated signals rather than to claim uncertainty over all possible oscillatory processes.

### Tennessee Eastman behavioral audit

A second evaluation examined whether the object representation exposed stable and
queryable changes in an observed industrial process without treating fault
classification as the primary criterion. The audit used mode 1 Tennessee Eastman
reactor-pressure trajectories for faults 1, 2, 4, 6, 7, 12, and 14. Five complete
simulation runs were evaluated for each fault. The selected faults were not assumed
to share one pressure response; they supplied heterogeneous cases in which the same
oscillation construction could succeed, produce weak changes, or cease to produce
complete objects.

For every run, reactor pressure was smoothed with a 20-sample window. Directional
states were calculated using a difference lag of 10 samples, and complete
trough–peak–trough objects were constructed with the alpha oscillation workflow.
The fault injection index was fixed at sample 600. Objects ending before sample 600
formed the run-specific pre-injection baseline. Objects overlapping the interval
from injection through sample 1200 formed the early-response regime. Later objects
formed the post-response regime. Objects were not divided into arbitrary fixed
windows: the regime label was attached to each complete behavioral interval.

Ten intrinsic properties were audited: rising duration, falling duration, total
duration, period, amplitude, rising mean rate, falling mean rate, peak rising rate,
peak falling rate, and temporal symmetry. Within each fault and complete simulation
run, the median of each early- and post-response property was compared with the
median of the same property's pre-injection objects. Signed Cliff's delta measured
the probability-of-superiority effect size. Positive values indicated that
post-injection objects tended to have larger property values than baseline objects;
negative values indicated smaller values.

Cross-run reproducibility was summarized independently for each fault, regime, and
property. A change was designated repeatable when at least 80% of the five runs
agreed on its direction and the absolute median Cliff's delta was at least 0.33.
This was an explicit descriptive reporting rule, not a learned decision boundary,
a significance test, or an estimate of diagnostic accuracy. The three strongest
properties per fault and regime were retained as a compact behavioral signature.
An object-coverage table included every fault–run–regime combination, including
combinations with zero complete objects.

The audit also executed ten deterministic questions against the resulting object
and summary tables. These queries retrieved extrema such as the largest-amplitude
and longest object for each fault, first objects overlapping the response, object
counts by regime, repeatable period and symmetry changes, and the strongest early
and sustained signature for each fault. Query execution evaluated whether the
representation made behavioral questions directly computable; it did not test
whether those questions were sufficient to identify an unknown fault.

### Reproducibility and scope

The evaluation emitted replicate-level tables, aggregate summaries, selected operating points, diagnostic results, figures, and a machine-readable manifest. Artifact hashes were recorded after generation so that the reported evaluation state could be checked independently. Tuning and testing used disjoint seed ranges, and the selected operating points were stored explicitly.

The experiment isolates a narrow question: how accurately does a specified trough–peak–trough construction recover known sinusoidal objects as sample noise increases? It does not evaluate automatic behavioral discovery, domain-specific validity, irregular sampling, nonstationary oscillations, or the wave-derived accumulation constructor. The BIDMC and Tennessee Eastman analyses are treated separately as cross-domain demonstrations because their object boundaries do not have equivalent analytical ground truth.
