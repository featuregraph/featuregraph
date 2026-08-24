# BIDMC respiratory-object workflow study

## Question

Can a researcher-authored behavioral construction be expanded into a complete,
auditable cohort study without allowing the execution layer to introduce
undeclared scientific rules?

## Source dataset

The study uses all 53 eight-minute recordings in the public
[BIDMC PPG and Respiration Dataset](https://physionet.org/content/bidmc/1.0.0/)
([DOI 10.13026/C2208R](https://doi.org/10.13026/C2208R)). Each record contains
physiological signals sampled at 125 Hz, including the impedance respiration
signal used here, together with breath annotations produced independently by
two annotators. The dataset was assembled from recordings acquired during
hospital care at Beth Israel Deaconess Medical Center.

The source publication is Pimentel et al., *Towards a Robust Estimation of
Respiratory Rate from Pulse Oximeters*, IEEE Transactions on Biomedical
Engineering 64(8), 1914-1923
([DOI 10.1109/TBME.2016.2613124](https://doi.org/10.1109/TBME.2016.2613124)).

## Frozen construction

The researcher input declares the 53-record BIDMC cohort, the raw respiration
signal, a 100-sample rolling-maximum followed by a 100-sample rolling-mean
envelope, offline alignment, a numerical tolerance of `1e-12`, directional
states, transition events, plateau-aware boundaries, trough-peak-trough object
identity, completeness rules, object measurements, comparison rules,
validation requirements, requested outputs, and interpretation limits.

The generated notebook applies that contract independently to every record.
For the state and event portion of the workflow, it passes the declared
`state-contract-v1` mapping to FeatureGraph's deterministic compiler. The
compiler materializes rising, falling, and inactive states, state-occurrence
identifiers, and entering- and exiting-rising boundaries. The runner stores the
canonical contract as JSON and records its SHA-256 fingerprint in provenance.

Preprocessing, plateau projection, trough-peak-trough identity, object
measurements, comparison, aggregation, and interpretation remain explicit
generated-study logic. Independent checks compare the compiled states and
event locations with the study's established deterministic formulas before the
full cohort regression checks are evaluated.

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
validation rules. It also demonstrates a bounded compiler integration: the
researcher-authored directional-state contract now drives the corresponding
state and event layer without changing the protected cohort outputs.

It does not establish clinical validity, automatic scientific discovery, or
ground truth for every discordant object.

## Reproducible record

- [Researcher input](../../notebooks/researcher_input/bidmc_researcher_input.ipynb)
- [Generated study](../../notebooks/generated_study/bidmc_generated_study.ipynb)
- [Workflow runner](../../scripts/run_bidmc_researcher_workflow.py)
- [Master framework paper](../paper/master/featuregraph_master_draft.md#6-bidmc-implementation-study)

From the repository root, install the package and run the complete workflow:

```bash
python -m pip install -e .
python scripts/run_bidmc_researcher_workflow.py
```

The runner downloads the public BIDMC source data, executes all 53 records, and
writes the generated notebook and validation artifacts declared by the study.

## Scope limitations

- The envelope is non-causal and uses a fixed study-specific smoothing window.
- The SciPy comparator and BIDMC annotations are external reference points, not
  universal ground truth.
- `state-contract-v1` compiles only the directional states and their enter/exit
  boundaries in this workflow. It does not compile preprocessing, plateau
  projection, object identity, measurements, comparisons, or interpretation.
- The remaining notebook binding still checks selected declarations and source
  fragments. The generated notebook was produced through assisted development;
  arbitrary researcher notebooks are not compiled automatically.
