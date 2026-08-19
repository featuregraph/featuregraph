# From Ordered Observations to Auditable Behavioral Objects: The FeatureGraph Framework

**Nazia Habib**  
**Consolidated master draft — August 19, 2026**

## Abstract

Scientific notebooks commonly combine investigator assumptions, data preparation, repeated execution, validation, and reporting in one evolving artifact. This makes it difficult to identify which choices came from the researcher, which were introduced for implementation convenience, and which were added by an assisting language model. FeatureGraph addresses this problem by converting ordered observations into explicit states, events, bounded objects, properties, and relations under a researcher-authored construction contract. A paired notebook workflow separates that contract from its mechanical execution. The researcher input notebook records study scope, signal mapping, preprocessing, state definitions, event boundaries, object identity, measurements, comparison rules, validation requirements, requested outputs, and interpretive limits. The generated study notebook expands the contract into executable cohort logic, object construction, matching, aggregation, regression checks, and reporting.

We examine the framework in two unrelated domains. On 53 BIDMC respiratory records, the current main-branch construction produces 7,926 complete trough-peak-trough objects, of which 7,086 match objects from a frozen SciPy comparator under an ordered one-to-one rule. On Tennessee Eastman Process simulations, a frozen reactor-pressure construction produces explicit peak events and peak-to-peak cycles, transfers across ten Fault 2 runs, and separates those runs from matched normal-operation windows while showing that reactor pressure alone is not specific to Fault 2. In both studies, discordant, incomplete, and ambiguous objects remain inspectable rather than being collapsed into a single performance score. FeatureGraph does not claim automatic scientific discovery, clinical validity, or a fault classifier. Its narrower contribution is a durable representation and workflow in which scientific choices, object boundaries, evidence, provenance, and failure limits remain explicit.

## 1. Introduction

A scientific analysis contains at least two kinds of work. The first is scientific and representational: selecting observations, deciding how a signal should be transformed, defining what constitutes a state or event, choosing object boundaries, specifying measurements, and limiting interpretation. The second is mechanical expansion: applying the same rules across records, checking files, assembling tables, matching objects, aggregating results, recording software versions, and rendering reports.

In an ordinary notebook these activities are interleaved. A threshold may appear beside a plotting command. A boundary rule may be embedded in a groupby operation. A cohort loop may silently apply different assumptions to different records. When an LLM assists with the implementation, an additional ambiguity appears: did the researcher choose the scientific rule, or did the model introduce it while making the code run?

FeatureGraph is developing a computational framework for transforming observation sequences into explicit behavioral objects. The framework treats behavior as structure that is present implicitly in an ordered signal and made explicit through declared construction rules. It distinguishes observations, sample-level states and events, bounded objects, object properties, relations, and semantic interpretation. Its purpose is not to infer the physical meaning of a signal from values alone. Its purpose is to preserve a researcher's assumptions as executable and inspectable contracts.

This paper presents a notebook-centered implementation of that idea. The workflow separates a researcher input notebook from a generated study notebook. The input notebook is the authoritative scientific specification. The generated notebook may implement repetition, matching, validation, aggregation, and reporting, but it may not add a scientific rule that is absent from the input. Together, the notebooks create an auditable path from researcher intent to object-level results.

The contributions of this draft are:

1. A division of responsibility between researcher-authored scientific input and generated execution.
2. A layered specification for behavioral time-series studies, including representation, construction, measurement, comparison, validation, and interpretation contracts.
3. An output workflow that retains observations, states, events, bounded objects, ambiguity, discordance, and provenance.
4. Worked implementations on the 53-record BIDMC respiration dataset and Tennessee Eastman Process simulations.
5. A transfer protocol that distinguishes representation success from domain diagnosis.
6. Evaluation criteria for extending the workflow without silently changing its representational assumptions.

This master draft concerns the framework and software workflow developed on the `main` branch. Frozen alpha and beta manuscripts remain historical study records. Their released implementations, counts, and claims are not rewritten here, and their results should not be combined numerically with the current main-branch study.

## 2. Problem formulation

Let a study begin with ordered observations

\[
X = \{(t_i, x_i, g_i)\}_{i=1}^{n},
\]

where \(t_i\) is time, \(x_i\) is an observed signal value, and \(g_i\) identifies an independent record or group. A behavioral construction maps observations to sample-level states and events, then partitions observations into bounded objects:

\[
X \xrightarrow{C} (S, E) \xrightarrow{B} O.
\]

Here, \(C\) is a construction contract, \(S\) contains persistent state predicates, \(E\) contains discrete transition events, \(B\) contains identity and boundary rules, and \(O\) is an object table with one row per candidate behavior. A measurement contract \(M\) maps each object and its supporting observations to intrinsic properties:

\[
(X, S, E, O) \xrightarrow{M} P.
\]

The challenge addressed here is not merely executing these mappings. It is preserving who supplied them and preventing the execution layer from changing them silently.

We therefore define two primary artifacts:

- **Researcher input notebook \(R\):** the authoritative declaration of study scope and scientific, representational, evaluative, and interpretive choices.
- **Generated study notebook \(G\):** the expanded implementation that executes the declarations in \(R\), materializes intermediate representations, validates invariants, and produces output artifacts.

The desired relationship is not that \(G\) contains no additional code. It necessarily contains more code. The requirement is that every scientific rule in \(G\) be traceable to \(R\). Mechanical implementation may expand; scientific authority may not migrate.

## 3. Layers of the study specification

The workflow separates concepts that are often collapsed into a single feature-engineering notebook.

### 3.1 Observed data

Observed data includes timestamps, measured values, record identity, ordering, missingness, and the preserved raw signal. Observations are not behavioral objects. They are the evidence from which objects are constructed.

### 3.2 Representation frame

The representation frame includes sampling rate, units, temporal resolution, observation duration, numerical precision, smoothing, normalization, and other declared preprocessing. These are not behaviors themselves. They determine the frame in which behavior is observed and measured.

### 3.3 Construction contract

The construction contract defines primitive states, transition events, object identity, boundaries, and completeness. For a directional signal construction, states might include rising, falling, and inactive. Entering or exiting a state creates an event. Events and cumulative identifiers partition observations into candidate objects.

### 3.4 Measurement contract

Measurements are derived only after the object has been defined. They may include start and end time, duration, magnitude, rate, period, symmetry, or a bounded accumulated quantity. A measurement is not allowed to define an object implicitly unless that dependency is declared in the construction contract.

### 3.5 Semantic context

Semantic context states what a signal represents and what a behavioral object may mean in a domain. The numerical construction alone does not establish that a wave is a breath, that a pressure episode is a fault, or that a discordant object is pathological. Domain interpretation can be attached to an object, but it must remain distinguishable from the object's computational definition.

These layers support a practical separation between intrinsic signal behavior, its measurement conditions, and the physical interpretation assigned by a researcher.

## 4. Researcher input notebook workflow

### 4.1 Purpose

The researcher input notebook is a compact, human-readable specification. In the current BIDMC implementation, the notebook contains exactly one code cell. The single-cell form is not a universal requirement, but it makes the authority boundary unusually clear: the cell is the complete human-authored scientific input, and the generated layer may not introduce a scientific rule that is absent from it.

The notebook is executable Python rather than a prose prompt. This allows the specification to express values, equations, lists, dictionaries, and invariants without depending on natural-language interpretation alone. At the same time, explanatory comments and named structures make the intent inspectable by a researcher.

### 4.2 Required content

The BIDMC researcher input declares:

- the development record and frozen 53-subject cohort;
- a 125 Hz sampling rate and expected file dimensions;
- preservation of the raw respiration signal;
- a fixed 100-sample max-then-mean envelope and its non-causal support;
- a numerical tolerance of \(10^{-12}\), explicitly identified as numerical rather than physiological;
- rising, falling, and inactive state predicates;
- entering-rising and exiting-rising events;
- projection of flat extrema to integer plateau midpoints;
- a trough-peak-trough respiratory-wave object definition;
- completeness, ambiguity, and truncation rules;
- the required object-table schema and property equations;
- a frozen SciPy comparator and ordered one-to-one matching rule;
- comparison with the two BIDMC breath-annotation series;
- mechanical and representational validation requirements;
- requested tables, cohort counts, agreement metrics, discordance metrics, and sensitivity checks;
- supported and unsupported interpretations;
- the allowed and prohibited responsibilities of the execution layer.

The input notebook therefore does more than provide parameter values. It supplies an executable research contract.

### 4.3 Human-LLM boundary

The current execution contract permits an assisting system to implement downloading, integrity checks, cohort repetition, object assembly, matching, validation, aggregation, regression tests, and reporting. It requires consultation before changing a threshold, filter, boundary, identity rule, completeness rule, matching rule, exclusion, imputation, property definition, or scientific interpretation.

This boundary is central to the workflow. The LLM may expand the researcher's cognition into software, but it may not become the silent source of scientific assumptions. When a new rule is required, the workflow should stop and return the decision to the researcher.

### 4.4 Input notebooks across domains

The repository also contains a Tennessee Eastman Process researcher input and generated study. The pair selects Fault 2, simulation run 10, and reactor pressure for development; preserves the raw signal; declares a max-then-mean processed signal; defines directional states, peak events, peak-to-peak objects, fragments, measurements, controls, transfer requirements, and interpretive limits; and applies the frozen construction across repeated Fault 2 simulations, normal-operation windows, and contrasting fault classes.

The distinction between domain mapping and reusable structure remains important. The TEP pair is not a respiratory notebook with renamed events. It uses the same representational layers while supplying its own signal semantics, validation evidence, and limits on diagnosis.

## 5. Generated study notebook workflow

### 5.1 Mechanical expansion

The generated study notebook takes the researcher contract and expands it into a complete executable study. For BIDMC, the generated notebook:

1. retrieves versioned source files;
2. verifies row counts, required columns, and missingness;
3. constructs an observation table for each subject;
4. preserves the raw signal and creates a separate envelope column;
5. materializes rising, falling, and inactive states;
6. materializes entering and exiting events;
7. projects numerical plateaus to explicit boundary intervals and representative midpoints;
8. assembles candidate wave objects;
9. retains incomplete, truncated, ambiguous, and invalidated candidates;
10. computes object properties from declared boundaries;
11. constructs the frozen comparator path;
12. performs ordered one-to-one object matching;
13. compares generated events with both annotation series;
14. repeats the same construction independently across all 53 subjects;
15. performs the declared sensitivity check;
16. executes frozen regression assertions and prints a report.

The generated notebook contains implementation detail that would obscure the research contract if it were placed in the input cell. Its role is to make the contract operational without changing its scientific content.

### 5.2 Output notebook as an inspectable record

The output notebook should remain readable at several levels. A reader can inspect the full cohort summary, but can also move downward to subject summaries, object tables, boundary intervals, state and event columns, and ultimately the raw supporting observations. This layered output is part of the FeatureGraph deliverable.

A behavioral object should be capable of supporting a human-readable account such as:

> Object TEP-10-017 is a complete pressure-transition episode beginning at 9.95 hours, changing phase at 10.80 hours, and ending at 11.62 hours. Its definition, supporting observations, measurements, and provenance are available for inspection.

This sentence is an illustrative design target, not a reported TEP result in the current study. The purpose is to show the expected relationship between a compact narrative and the object-level evidence beneath it.

### 5.3 Output bundle

The workflow is designed to preserve more than the rendered notebook. The current BIDMC runner defines an output bundle containing:

- per-subject observation, state, and event tables;
- complete FeatureGraph objects;
- comparator objects;
- matched, FeatureGraph-only, and comparator-only objects;
- invalidated and ambiguous objects;
- subject, cohort, annotation, and sensitivity summaries;
- console output;
- a validation report;
- software and platform versions;
- repository commit identifiers;
- hashes of the researcher input and execution notebook.

The notebook is therefore one view of the result. The durable result is a linked set of specifications, code, object tables, validation records, and provenance.

### 5.4 Binding input to execution

The current prototype parses declarative assignments from the researcher notebook, validates frozen values, verifies that required implementation fragments appear in the generated notebook, executes the notebook, and records hashes of both artifacts. This prevents accidental execution of a visibly inconsistent study.

The binding is not yet a semantic compiler. String-fragment checks can confirm that selected frozen parameters and calls are present, but they cannot prove that all execution logic is equivalent to the researcher specification. The workflow currently combines explicit contracts, regression assertions, artifact hashes, and review. A future implementation should replace hard-coded binding checks with a typed intermediate specification from which both execution and validation can be generated.

## 6. BIDMC implementation study

### 6.1 Construction

The complete implementation uses BIDMC version 1.0.0, subjects 1 through 53, and the respiration signal sampled at 125 Hz. For each record, the raw signal is retained. A separate offline envelope is constructed by a 100-sample rolling maximum followed by a 100-sample rolling mean and a negative 100-sample shift. The resulting effective support is 199 samples, or approximately 1.592 seconds.

The first difference of the envelope defines local directional change. A valid sample is rising when the change exceeds \(10^{-12}\), falling when it is below \(-10^{-12}\), and inactive when its absolute value is at most \(10^{-12}\). The tolerance separates floating-point residue from directional change; it is not a physiological amplitude threshold.

Entering the rising state marks a trough transition, and exiting the rising state marks a peak transition. Because the state describes the edge ending at the current row, the extremum event is projected to the preceding sample. Numerically flat extrema are represented as intervals. Each object boundary is projected to the floor midpoint of its complete plateau interval.

One candidate respiratory-wave object is a trough-peak-trough interval. A complete object requires a starting trough, an interior peak, a following trough, strict temporal ordering, complete leading and trailing boundaries, and non-overlapping projected plateau intervals. Incomplete and ambiguous candidates remain in the object table with flags.

### 6.2 Generated results

The generated notebook completed all 53 records with no execution failures. It produced:

| Output | Count |
| --- | ---: |
| Detected FeatureGraph peaks | 7,988 |
| Complete FeatureGraph objects | 7,926 |
| Complete comparator objects | 7,168 |
| Matched objects | 7,086 |
| FeatureGraph-only objects | 840 |
| Comparator-only objects | 82 |
| Plateau-ambiguous objects | 90 |
| Formerly complete candidates invalidated by overlapping plateaus | 37 |

Across the 7,086 matched object pairs, the median absolute peak-location difference is 6.5 samples, or 0.052 seconds. The median absolute differences are 0.311 breaths per minute for derived rate, 0.056 seconds for period, 0 for full excursion, and 0.0966 for temporal symmetry. These values characterize the generated workflow relative to the frozen comparator; they do not establish clinical validity or superiority.

Of the 840 FeatureGraph-only objects, 474 are excluded by both BIDMC annotation series and 366 are retained by at least one annotation series. Discordance is therefore preserved as structured output rather than assigned a single truth label.

### 6.3 Numerical-boundary correction as workflow evidence

Inspection of subject 13 exposed floating-point changes of approximately \(5.55 \times 10^{-17}\) in a numerically flat envelope region. Under an exact-zero state boundary, this residue created repeated state transitions and spurious object identifiers. The researcher contract was amended to include the fixed numerical tolerance of \(10^{-12}\), while explicitly excluding physiological interpretation. A regression fixture now contains the observed residue and a genuine envelope change of approximately \(9.7 \times 10^{-6}\).

The correction removed 207 complete FeatureGraph-only objects without changing any of the 7,086 matched objects. This episode demonstrates the intended workflow: an implementation failure was localized in the state/event representation, the scientific meaning of the correction was classified, the contract was updated, and the output was protected by a regression assertion.

## 7. Tennessee Eastman Process transfer study

### 7.1 Construction

The Tennessee Eastman Process (TEP) study tests whether the same representation sequence can be applied to a different physical system without treating the respiratory waveform class as the framework. Fault 2, simulation run 10, is the development record, and reactor pressure is the observed signal. The raw signal is preserved. A separate processed signal is formed by a 50-sample rolling maximum, a 50-sample rolling mean, and an offline alignment shift of -50 samples. Rising, falling, and inactive states are defined from the sign of the aligned pressure rate. Exits from rising define peak events. Consecutive peak events bound half-open peak-to-peak cycle objects; leading and trailing fragments remain represented as incomplete.

This construction shares mechanics with BIDMC—preserved observations, a derived envelope, directional states, transition events, bounded identity, object properties, and explicit fragments—but it does not import respiratory semantics. The objects are pressure cycles, not breaths, and a pressure peak is not by itself a fault label.

### 7.2 Frozen transfer

On the development run, the construction produces 32 valid peak events, 31 complete cycles, and two boundary fragments. The dominant aligned peak occurs at index 637 (10.62 hours) with pressure 2806.58. The frozen construction is then applied without run-specific tuning to the other nine Fault 2 simulations. Every run produces a dominant peak between indices 630 and 687, and maximum aligned peak pressure ranges from 2804.96 to 2807.60.

For a negative control, the 500-hour normal Mode 1 record is divided into ten non-overlapping 50-hour windows. All ten Fault 2 runs exceed all ten normal windows in maximum aligned peak pressure and peak excess over the run median. Prominence and peak-event count do not separate the two cohorts. The representation therefore preserves multiple properties rather than selecting only the measurements that support separation.

### 7.3 Specificity boundary

The same frozen construction is applied to simulation run 10 from the other 20 fault classes. Ten classes equal or exceed Fault 2 run 10 in peak excess, and Faults 1 and 7 also produce large early pressure peaks near the Fault 2 event time. Reactor pressure therefore identifies a repeatable abnormal response associated with Fault 2 in this cohort, but it does not uniquely identify Fault 2.

This negative specificity result is an important framework result. The pressure object is still a valid representation of an excursion even when it is insufficient for diagnosis. A more specific fault representation may require relations among objects from several signals, but the original pressure-cycle definition should not be retrospectively altered merely to manufacture specificity.

## 8. Evaluation criteria for reusable workflows

A reusable FeatureGraph workflow should be evaluated along dimensions that are not captured by a single detector score.

### 8.1 Contract fidelity

Every scientific and representational rule in the generated study should be traceable to the researcher input. Changes should be visible as changes to the input contract rather than hidden inside execution code.

### 8.2 Determinism and repeatability

Given the same versioned observations, specification, software environment, and repository state, the workflow should reproduce the same state columns, events, boundaries, object tables, and validation results.

### 8.3 Inspectability

Every object should retain a path to its supporting observations, state assignments, boundary events, completeness flags, measurements, and provenance. Summary reports should not replace these intermediate layers.

### 8.4 Boundary honesty

Incomplete, ambiguous, overlapping, and truncated objects should remain explicit. A reusable framework should not manufacture completeness to simplify downstream analysis.

### 8.5 Transfer

For a domain-transfer claim, the same state definitions, event operators, boundary rules, object schema, and measurement equations should be applied to an unrelated physical domain. Dataset adapters, signal mappings, units, and declared preprocessing may differ. Repeated domain-specific intervention is evidence that the abstraction or ingestion layer requires revision.

### 8.6 Intervention burden

The workflow should record every manual intervention required to make the construction execute. A method that transfers only after substantial unreported tuning is not a transferable representation.

## 9. Discussion

### 9.1 Beyond ordinary feature engineering

Feature engineering usually produces columns selected for a downstream task. The present workflow produces a layered representation: observations, states, events, boundaries, object identity, intrinsic properties, relations, and provenance. The object table is not simply a compressed signal. It is an index into the construction that produced each bounded behavior.

The input/output notebook division also changes the role of an LLM. The model is not asked to provide an opaque analysis whose assumptions must be inferred afterward. It is asked to expand a researcher-owned specification into code and artifacts under an explicit authority boundary.

### 9.2 Externalized scientific cognition

The researcher input notebook externalizes assumptions that might otherwise remain distributed across code, conversation, and memory. The generated notebook externalizes the mechanical consequences of those assumptions. Together they create a platform from which the researcher can inspect errors, revise definitions, compare domains, and build further studies.

This does not remove the difficulty of scientific reasoning. It makes the location of that reasoning more visible. When a generated workflow encounters an undefined boundary or a new domain-specific condition, the correct response is not to hide the decision in implementation code. It is to return the unresolved choice to the research contract.

### 9.3 Automation and scientific discovery

The current workflow automates parts of scientific analysis: repeated construction, validation, matching, aggregation, provenance capture, and production of inspectable object tables. It may support scientific discovery by making unusual or discordant behaviors easier to localize and compare. It does not autonomously determine which behaviors are scientifically important, establish causal explanations, or validate domain interpretations.

The defensible claim is therefore that FeatureGraph automates portions of the construction and preservation of scientific workflows. Whether this accelerates discovery must be evaluated through future studies.

## 10. Limitations

The repository contains complete researcher-input/generated-study pairs for BIDMC and TEP, but the two studies are not equivalent forms of validation. BIDMC has comparator objects and two annotation series; TEP has repeated simulations, normal-operation windows, and a one-run-per-class specificity check. Neither evidence design supplies universal ground truth.

The researcher input is executable Python rather than a typed formal specification. This provides flexibility but permits arbitrary code and makes complete semantic validation difficult.

The generated study notebook is presently produced through an assisted development process and then bound to selected input values. The system does not yet compile an arbitrary researcher notebook automatically into a complete study.

The binding script validates declared assignments, selected implementation fragments, regression outputs, and artifact hashes. These checks are useful but do not prove semantic equivalence between the input and generated notebooks.

The BIDMC construction includes a non-causal envelope and a fixed smoothing window chosen for this study. Neither is claimed to be universally appropriate. The comparator and annotations provide external reference points, not ground truth for every object.

The TEP normal controls are windows from one continuous normal record rather than independent normal simulations, and the cross-fault check uses one matched run per contrasting class. Both constructions use offline alignment with future observations, so causal deployment would require separate event and detection times.

The workflow has not yet formalized object composition and relations across multiple signals, overlapping objects, nested behaviors, or irregular sampling. Two domains demonstrate controlled transfer, not universal applicability.

## 11. Toward a complete FeatureGraph framework

The next implementation stage is to turn the successful BIDMC pair into a reusable workflow across domains. The required deliverables are:

1. A typed researcher specification that separates dataset mapping, representation frame, construction, measurement, validation, requested output, and interpretation.
2. A stable observation interface for timestamps, signals, groups, units, missingness, and preprocessing provenance.
3. Reusable operators for states, enter/exit events, identities, intervals, bounded measurements, and relations.
4. A generated notebook template that expands a specification without introducing undeclared scientific rules.
5. An output bundle containing observation tables, object tables, relations, readable object narratives, validation, and provenance.
6. Binding tests that operate on a structured intermediate representation rather than source-code fragments.
7. At least one unrelated physical-domain study using the same object contract and stable schema.
8. A transfer report that distinguishes unchanged contracts, allowed adapters, manual interventions, failures, and required extensions.

The completed Tennessee Eastman pressure study supplies the first unrelated-domain transfer. The next test should construct relations among multiple TEP signals without changing the pressure-cycle object merely to improve fault specificity.

## 12. Conclusion

This paper presents a software workflow for converting researcher-authored behavioral definitions into auditable generated studies. The researcher input notebook records the scientific and representational contract. The generated notebook implements repetition, object assembly, comparison, validation, aggregation, and reporting while retaining the observations, states, events, boundaries, and provenance needed to inspect every result.

The BIDMC implementation shows that this separation can support a complete 53-record workflow with frozen assumptions, object-level outputs, explicit discordance, numerical-boundary regression tests, and reproducibility metadata. The TEP implementation shows that the same representational sequence can construct useful objects in an unrelated physical system while exposing the boundary between abnormal-response representation and fault diagnosis. The result is not an autonomous scientist and not a universal language of physical behavior. It is a concrete mechanism for preserving researcher intent while using software and LLM assistance to expand that intent into repeatable, inspectable studies.

## References

References to related work in scientific workflow systems, computational notebooks, provenance, executable specifications, time-series representation, and human-LLM collaboration will be added after the framework and comparison set are frozen.
