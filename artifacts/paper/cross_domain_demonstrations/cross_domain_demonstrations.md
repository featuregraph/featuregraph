## Cross-domain demonstrations

The synthetic evaluation isolates whether the alpha implementation can recover known oscillatory objects under controlled conditions. The following demonstrations address a different question: whether the same construction and object representation can be applied to observed signals from unrelated physical systems. They are not domain-validation studies and do not supply independently annotated ground truth. Their purpose is to demonstrate representational reuse, inspectability, and object-level analysis after construction.

FeatureGraph v0.1.0a1 was applied to two fixed datasets: respiration observations from subject 1 of the BIDMC PPG and Respiration Dataset and reactor-temperature observations from mode 1, fault 1, simulation run 1 of the Tennessee Eastman process dataset. These signals differ in source, scale, sampling context, and physical interpretation. The same alpha workflow was nevertheless used in both cases:

1. select an ordered signal and its grouping variables;
2. optionally smooth the signal;
3. construct rising and falling states;
4. derive peak and trough events from directional reversals;
5. assign trough–peak–trough oscillation identities;
6. distinguish complete from boundary-truncated objects;
7. calculate object properties; and
8. return both sample-level construction evidence and an object summary table.

The shared workflow does not assert that breathing and reactor behavior are physically equivalent. It asserts only that both selected signals contain repeated directional structures that can be represented by the same formal object type.

### BIDMC respiration

The BIDMC demonstration used the respiration channel for subject 1. No individual respiratory cycle was manually marked. The alpha oscillation constructor operated on the ordered observations and returned rising and falling states, entry and exit events, extrema locations, oscillation identifiers, and object-relative measurements. Its summary representation contained one row for each complete oscillation.

The resulting objects exposed a common set of structural fields: oscillation identity, start, peak and end indices, rising and falling durations, total duration, period, amplitude, temporal symmetry, and completeness evidence. The same result also retained the expanded sample-level table and the parameters used during construction. An analyst could therefore move in either direction: from a summary row back to the evidence supporting that object, or from the complete object table to aggregate questions about respiratory behavior.

The alpha demonstration constructed 1,070 complete respiration oscillations. Once represented as objects, the signal could be queried without detecting its cycles again. For example, filtering for duration greater than or equal to 100 samples returned 175 objects, or 16.36% of the complete oscillations. Additional predicates could be combined to retrieve long objects with nearly balanced rising and falling phases, after which the selected objects could be ordered by amplitude.

This example illustrates the distinction between filtering observations and querying behaviors. A condition such as “duration greater than or equal to 100” cannot be evaluated directly against an undifferentiated respiratory trace because duration belongs to a bounded occurrence. The oscillation construction supplies the identity and boundaries required for that predicate to have a computational meaning. The subsequent query is simple because the representational work has already been performed.

### Wave-derived respiratory accumulation

The respiration demonstration also supplied the parent intervals for the alpha accumulation construction. Within each oscillation, the minimum observed value defined a wave-specific baseline. Subtracting that baseline produced a contribution series, and a discrete cumulative sum produced the accumulation trajectory. The resulting accumulation object shared its identifier and temporal extent with its parent oscillation.

Each accumulation summary exposed total area above baseline and object-relative measures including accumulation rate, accumulation symmetry, centroid time, half-accumulation time, and accumulation before and after the oscillation peak. This made it possible to ask questions that combined geometric and cumulative descriptions of the same occurrence. For example, an accumulation object could be selected by total area and then related directly to the duration, amplitude, or temporal symmetry of its parent oscillation.

The demonstration is intentionally limited to wave-derived accumulation. It does not imply that every accumulation process is oscillatory or that the wave minimum is a generally appropriate baseline. It shows that once a parent object provides an explicit interval, a second behavioral representation can be constructed inside that interval and related to the parent without rediscovering temporal membership.

### Tennessee Eastman reactor temperature

The second demonstration used reactor temperature from one fixed Tennessee Eastman fault simulation. The data were grouped by fault number and simulation run, and a rolling smoothing window of 20 samples was applied before directional-state construction. Smoothing was part of the declared construction because local noise otherwise produced reversals at a scale not intended for the demonstration.

After this preprocessing difference, the same oscillation pipeline used for respiration constructed trough–peak–trough objects from the reactor-temperature signal. The output used the same object schema as the respiration result. Start, peak and end locations retained their roles; rising and falling durations described the two phases; amplitude summarized within-object range; temporal symmetry expressed balance between phase durations; and completeness indicated whether the required landmarks were present in the observed group.

The shared schema allows downstream software to consume either result using the same structural vocabulary. A query mechanism can filter objects by duration, amplitude, symmetry, or completeness without containing separate logic for respiratory physiology and chemical-process simulation. Grouping fields and construction metadata retain the dataset-specific context, while the object fields retain the common behavioral structure.

This separation is important. A reactor-temperature oscillation and a respiratory oscillation should not be pooled merely because their tables share column names. Their units, mechanisms, scientific meanings, and appropriate thresholds remain domain dependent. Schema compatibility makes common computational operations possible; it does not establish scientific exchangeability.

### Demonstrated representational invariants

Across the two domains, four elements remained invariant.

First, object identity was explicit. Every summarized occurrence could be addressed independently rather than inferred repeatedly from sample positions.

Second, temporal structure was explicit. Each complete object contained an ordered start–peak–end configuration and associated phase durations.

Third, provenance remained available. The object table did not replace the states, events, identifiers, grouping information, or construction parameters from which it was produced.

Fourth, the output was queryable as an ordinary table. Selection, ordering, grouping, joining, visualization, and downstream modeling could operate on behavioral occurrences rather than raw samples.

The varying elements were the observed signal, grouping variables, preprocessing choice, parameterization, scale, and domain interpretation. This division between structural invariants and domain-specific choices is the principal result of the demonstrations. FeatureGraph does not remove the need to decide whether an oscillatory construction is appropriate. It makes the consequences of that decision explicit and reproducible.

### Demonstration scope

These examples establish feasibility rather than domain accuracy. Neither dataset includes the object-level annotations required to estimate detection precision, boundary error, or property error for the demonstrated physical signals. Visual plausibility and the ability to form coherent object tables are insufficient substitutes for expert or instrumented ground truth.

The demonstrations also cover only one subject and one simulation selection. They do not establish population-level respiratory findings, fault-diagnostic performance, or generalization across Tennessee Eastman operating modes. Reported counts and queries describe the fixed selections and construction parameters recorded by the reproduction package.

Within those limits, the demonstrations show that the alpha implementation can transform unrelated observed signals into the same kind of computational artifact: a table of bounded oscillatory objects supported by inspectable construction evidence. The synthetic evaluation assesses when those boundaries are reliable; the cross-domain examples show what becomes possible once such a representation has been constructed.
