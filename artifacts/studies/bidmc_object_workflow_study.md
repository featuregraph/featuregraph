# BIDMC respiratory-object workflow study

## Question

Can a researcher-authored behavioral construction be expanded into a complete,
auditable cohort study without allowing the execution layer to introduce
undeclared scientific rules?

## Frozen construction

The researcher input declares the 53-record BIDMC cohort, the raw respiration
signal, a 100-sample rolling-maximum followed by a 100-sample rolling-mean
envelope, offline alignment, a numerical tolerance of `1e-12`, directional
states, transition events, plateau-aware boundaries, trough-peak-trough object
identity, completeness rules, object measurements, comparison rules,
validation requirements, requested outputs, and interpretation limits.

The generated notebook applies that contract independently to every record. It
retains raw observations, sample-level states and events, complete and
incomplete candidates, object tables, comparator matches, annotation
comparisons, cohort summaries, sensitivity evidence, and provenance.

## Recorded results

| Output | Count |
| --- | ---: |
| BIDMC records completed | 53 |
| Detected FeatureGraph peaks | 7,988 |
| Complete FeatureGraph objects | 7,926 |
| Complete comparator objects | 7,168 |
| Matched objects | 7,086 |
| FeatureGraph-only objects | 840 |
| Comparator-only objects | 82 |
| Plateau-ambiguous objects | 90 |
| Candidates invalidated by overlapping plateaus | 37 |

Across the 7,086 matched pairs, the median absolute peak-location difference is
6.5 samples, or 0.052 seconds. Of the 840 FeatureGraph-only objects, 474 are
excluded by both BIDMC annotation series and 366 are retained by at least one.
Discordance therefore remains inspectable rather than being assigned a single
truth label.

## Numerical-boundary correction

Subject 13 exposed floating-point changes of approximately `5.55e-17` in a
numerically flat envelope region. The exact-zero boundary created repeated
state changes and spurious identities. Declaring the fixed numerical tolerance
removed 207 complete FeatureGraph-only objects without changing any of the
7,086 matched objects. The regression fixture distinguishes that residue from a
genuine envelope change of approximately `9.7e-6`.

## Supported conclusion

The study demonstrates a complete paired-notebook workflow in which a declared
construction is executed across 53 records and produces inspectable
observation-, event-, and object-level evidence with frozen comparison and
validation rules.

It does not establish clinical validity, automatic scientific discovery, or
ground truth for every discordant object.

## Reproducible record

- [Researcher input](../../notebooks/researcher_input/bidmc_researcher_input.ipynb)
- [Generated study](../../notebooks/generated_study/bidmc_generated_study.ipynb)
- [Workflow runner](../../scripts/run_bidmc_researcher_workflow.py)
- [Master framework paper](../paper/master/featuregraph_master_draft.md#6-bidmc-implementation-study)

## Scope limitations

- The envelope is non-causal and uses a fixed study-specific smoothing window.
- The SciPy comparator and BIDMC annotations are external reference points, not
  universal ground truth.
- The notebook-binding prototype checks selected declarations and hashes but is
  not yet a semantic compiler.
- The generated notebook was produced through assisted development; arbitrary
  researcher inputs are not yet compiled automatically.
