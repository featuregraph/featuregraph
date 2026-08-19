## Discussion and limitations

### Representation after detection

The alpha results support a distinction between detecting a landmark and representing a behavior. Specialized detection methods can locate peaks or change points effectively, but downstream questions usually concern bounded occurrences: how many occurred, where each began and ended, whether an occurrence was complete, how its internal phases were organized, and what properties belonged to it. FeatureGraph addresses this latter problem by carrying sample-level evidence into explicit object identities and summary tables.

The synthetic comparison makes the distinction concrete. SciPy was the stronger detector for the noisy sinusoidal benchmark, particularly above noise standard deviation 0.10. FeatureGraph nevertheless added representational structure not supplied by a peak list alone: rising and falling states, entry and exit events, trough–peak–trough membership, completeness, object properties, parent–child accumulation identity, and a queryable table. These outputs do not negate inferior detection performance. They begin after a detector or state construction has provided usable boundaries.

FeatureGraph should therefore not be understood as requiring one universal detection mechanism. The alpha binds its representation to a directional-state construction, but the broader framework permits object boundaries to originate from other deterministic procedures. A mature implementation could accept landmarks produced by specialized peak detectors, domain rules, validated segmentation algorithms, or externally supplied annotations, provided their semantics and provenance remain explicit. The evaluation suggests that this separation is not merely architectural preference: detector quality can dominate object quality under noise.

### What explicit objects make available

Once behavior is represented as one row per occurrence, several operations become ordinary data manipulation rather than repeated signal interpretation. Objects can be counted, filtered by intrinsic properties, compared across groups, joined to related objects, visualized by identity, or supplied to statistical and machine-learning systems. A request for long, high-amplitude, or temporally balanced oscillations becomes a predicate over declared fields.

This does not mean that queries create new scientific meaning automatically. Thresholds remain context dependent, and the same numerical property can have different interpretations across systems. The contribution is that the prerequisites for querying—identity, boundaries, membership, and measurements—are available in a stable computational form.

The BIDMC demonstration illustrates this shift. The statement that 175 of 1,070 complete respiratory oscillations lasted at least 100 samples is reproducible because each oscillation has an identifier and duration. Without the object table, the same statement would conceal a prior, potentially repeated decision about cycle boundaries. The object representation makes that dependency visible.

### Provenance as part of the representation

Determinism alone is insufficient if the construction parameters are lost. Smoothing, comparison lag, tolerance, grouping, and boundary conventions change what the resulting objects mean. In the held-out experiment, the tuned FeatureGraph operating point detected all clean objects but displaced their landmarks because its 9-sample smoothing window and 10-sample difference lag changed the boundary semantics. Object count alone would have hidden this effect.

The alpha returns both the object summary and the expanded sample-level features used to construct it. This allows a summary row to be traced to its states, events, landmarks, and source observations. Construction metadata records the declared parameters. Such provenance is especially important when object tables are reused outside the notebook or process that created them. A downstream consumer should not have to infer whether boundaries were formed from raw values, a smoothed signal, or a lagged comparison.

This approach also supports falsification. If an object appears implausible, its construction evidence can be inspected. The analyst can determine whether the issue arose from a noisy reversal, an unsuitable smoothing scale, an edge-truncated interval, or a property calculation. Explicit intermediate representations turn these possibilities into testable implementation questions.

### Cross-domain reuse without semantic collapse

The respiration and reactor-temperature demonstrations show that a common structural schema can be reused across unrelated signals. Both results contain bounded oscillations with start, peak and end landmarks and the same family of object properties. This compatibility permits generic downstream code to consume either table.

The shared schema should not be mistaken for a claim that the objects are scientifically interchangeable. Respiratory and reactor-temperature cycles arise from different mechanisms, use different units, and support different domain questions. Even identically named properties may require different scales and thresholds. FeatureGraph separates a reusable structural vocabulary from domain interpretation; it does not remove domain interpretation.

This limitation is also a design constraint for future cross-domain repositories. Objects from different systems should be related only through declared metadata, ontologies, units, construction semantics, and scientifically justified mappings. Schema equality is evidence of computational compatibility, not of causal or physical equivalence.

### Composition

Wave-derived accumulation demonstrates that one behavioral object can provide context for another. The parent oscillation supplies a temporal interval, object identity, peak landmark, and within-wave baseline. The child accumulation then describes how contribution is distributed through that interval. Because the identifiers align, geometric and cumulative properties can be joined without temporal rematching.

This is a limited but important example. Many behavioral quantities require an interval before they can be defined. Explicit composition makes that dependency visible. It also prevents the secondary measure from being calculated over arbitrary windows unrelated to the parent behavior.

The alpha accumulation construction should not be generalized beyond its implemented semantics. It uses a discrete cumulative sum of the signal above the within-wave minimum. It does not multiply by a physical sampling interval, and it is not a universal model of stored mass, energy, heat, reward, or dose. Applications with physical accumulation require an appropriate baseline, integration rule, units, sampling treatment, and possibly an independently constructed interval.

### Limitations of the alpha detector

The principal empirical limitation is noise sensitivity. The alpha’s local directional states can fragment when noise introduces additional reversals. At noise standard deviation 0.40, mean F1 fell to 0.595, with precision declining more strongly than recall. This indicates the formation of additional candidate objects rather than only missed true cycles. SciPy retained mean F1 of 0.910 under the same conditions.

Smoothing and comparison lag reduced fragmentation but introduced systematic landmark displacement. The tuned operating point placed clean-signal starts, peaks, and ends approximately 8–10 samples from the analytical indices even while detecting every object. These are not random localization errors alone; they reflect the semantics of the chosen transformation. Parameters that improve object identity under noise may therefore reduce agreement with raw-signal extrema.

FeatureGraph results were also parameter sensitive. The strongest tuning settings clustered around a smoothing window of 9 and lag of 10, whereas unsmoothed and short-lag settings often fragmented the signal severely. The framework makes these choices reproducible but does not select them automatically or guarantee that one operating point transfers to another signal.

The synthetic generator was intentionally simple: a regular sinusoid with additive noise. It does not represent irregular periods, drifting baselines, nested frequencies, flat extrema, missing observations, nonstationary sampling, abrupt regime changes, or interacting oscillations. Performance on those conditions remains unestablished.

### Limitations of the evaluation

The comparison was conducted on one synthetic family and one specialized baseline. It does not establish broad comparative ranking against contemporary peak detection, segmentation, change-point, or time-series representation methods. SciPy was given a period-informed distance grid, while FeatureGraph was tuned over smoothing, lag, and epsilon. The experiment describes these fixed search spaces; it does not prove that either method was globally optimized.

Localization and property errors were calculated only for matched objects. At higher noise levels, the most severely incorrect detections were expressed through precision and recall rather than through conditional mean absolute error. Consequently, small amplitude or duration error among matched FeatureGraph objects must not be interpreted as high overall accuracy when F1 is low.

The confidence intervals summarize variation across finite synthetic noise realizations, not uncertainty across real physical systems. The exact-recovery experiment verifies implementation consistency under construction-aligned clean conditions; it does not imply exact recovery whenever a real signal appears clean.

### Interpretive value of the behavioral audit

The Tennessee Eastman audit clarifies where the alpha representation adds value
without requiring a prediction claim. Raw samples can be plotted or passed to a
model, but they do not directly identify which oscillatory occurrence was longest,
which transition was fastest, whether a change persisted after the response
interval, or whether the same object property changed in the same direction across
runs. FeatureGraph externalized those distinctions into bounded records that could
be compared and queried with ordinary table operations.

The heterogeneous fault results are important. A useful representation should not
manufacture the same signature for every condition. Faults 1, 6, 12, and 14
produced distinct repeatable profiles; Faults 2, 4, and 7 did not. Fault 6 exposed a
different failure mode by producing no complete post-response objects. These
outcomes suggest that FeatureGraph can function as an audit layer that makes both
behavioral evidence and representational insufficiency visible.

The audit does not show that FeatureGraph features are sufficient statistics for
fault identification or that they outperform raw observations in a classifier.
The fault number and injection time were known, and the analysis asked how object
properties changed relative to a within-run baseline. This reverses the usual
prediction question: rather than inferring an unknown label, it tests whether a
known intervention leaves a stable and interpretable behavioral trace. That design
is appropriate for evaluating representation, but it does not estimate diagnostic
sensitivity, specificity, or deployment performance.

The results also make signal and construction selection part of the scientific
claim. Weak reactor-pressure signatures do not establish that Faults 2, 4, and 7
lack process effects; another measured variable or behavioral object may represent
those faults more directly. Likewise, zero complete Fault 6 post-response objects
may indicate a changed physical regime, an unsuitable trough–peak–trough
construction, or both. Future evaluation should pair object tables with raw traces,
partial-object coverage, alternative signals, and domain knowledge before assigning
mechanistic meaning.

### Limitations of the demonstrations

The BIDMC and Tennessee Eastman signals lack independently annotated oscillation boundaries. The synthetic experiment evaluates boundary recovery under known ground truth, but the observed-domain demonstrations evaluate construction, inspectability, and behavioral comparison rather than object-detection accuracy. They do not establish physiological validity or correct physical interpretation of every constructed object.

The fixed BIDMC reproduction still covers only one subject, and the original reactor-temperature demonstration covers one fault run. The reactor-pressure audit broadens process coverage to seven faults and five runs per fault, but it does not cover all Tennessee Eastman faults, operating modes, signals, preprocessing choices, or sampling regimes. Its repeatability summaries describe the selected construction and should not be treated as population-level diagnostic conclusions.

Duration is expressed in sample or index units unless timestamps and sampling intervals are explicitly incorporated. Cross-dataset comparisons of duration, rate, accumulation, or amplitude require compatible units and sampling semantics. The shared table schema does not perform those conversions.

### Implementation and scope limitations

FeatureGraph v0.1.0a1 is a pandas-based alpha research implementation. It focuses on oscillations and wave-derived accumulation, not a complete library of behavioral types. Its API, object definitions, and execution model should not be interpreted as a finalized public standard.

The alpha does not discover scientifically meaningful states without specification. Rising and falling are useful for the demonstrated signals, but other behaviors may require thresholds, multivariate conditions, domain events, learned detectors, or relations among several signals. State discovery and domain validation remain outside the demonstrated scope.

Irregular sampling is described conceptually but is not fully evaluated. The alpha’s discrete duration and cumulative operations are most directly interpretable for ordered, regularly sampled data. Missingness, timestamp-aware integration, streaming updates, overlapping objects, nested objects, and distributed execution remain future work.

### Implications

The results suggest a practical division of labor. Detection methods should be selected and validated for the signal and noise regime. FeatureGraph-like machinery can then externalize the resulting behavioral distinctions into persistent objects with boundaries, identities, properties, provenance, composition, and queryability. Improving the representational layer does not remove the need for reliable detection; it reduces the amount of downstream work that must be repeated after detection.

The alpha establishes this idea narrowly but concretely. It shows that behavioral objects can be constructed deterministically, inspected at sample level, summarized at object level, composed into related representations, and reused across domains. Its limitations identify the next requirements: detector modularity, explicit boundary semantics, broader behavioral definitions, timestamp-aware measures, validation on annotated real signals, and stronger mechanisms for comparing or relating objects without erasing domain meaning.
