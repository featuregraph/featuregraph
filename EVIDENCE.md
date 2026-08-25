# FeatureGraph: research-engineering evidence

FeatureGraph is a deterministic system for turning researcher-declared rules over time-series data into inspectable states, events, bounded occurrences, measurements, relations, and validation records. The evidence below is organized for verification: each claim links to the study record, implementation, and—where available—focused tests or a complete rerun path.

## Start here: two end-to-end studies

### 1. Preserve a published physiological protocol without inventing missing meaning

Across 33 eligible participants from two versions of a public PhysioNet stress protocol, FeatureGraph materialized 248 declared protocol occurrences while preserving all 248 start and end boundaries exactly. Every occurrence joined to its source self-report and contained native-rate heart-rate, electrodermal-activity, and temperature samples; 99 of 99 compiler validation checks passed. The two protocol versions use different tag adapters but produce one object schema and the same measurement equations. Time not assigned by the source protocol remains explicitly `unassigned`.

- [Study and verification table](https://github.com/featuregraph/featuregraph/blob/main/artifacts/studies/physionet_wearable_protocol_study.md)
- [Executable study](https://github.com/featuregraph/featuregraph/blob/main/scripts/run_physionet_wearable_protocol_study.py)
- [Focused protocol and boundary tests](https://github.com/featuregraph/featuregraph/blob/main/tests/test_physionet_wearable_protocol_study.py)
- [Compiler implementation](https://github.com/featuregraph/featuregraph/blob/main/src/featuregraph/contracts/state_contract.py)

**What this demonstrates:** dataset interpretation, schema design across protocol versions, lossless joins, preservation of native-rate signals, explicit handling of exclusions and undeclared intervals, executable validation, and disciplined scientific claim boundaries.

**Claim boundary:** this represents the authors' published protocol. It does not detect stress, establish causality, or validate a physiological biomarker.

### 2. Turn a researcher-authored construction into an auditable 53-record workflow

The BIDMC study executes a declared respiratory-object construction independently across all 53 public eight-minute records. It produces 7,926 complete FeatureGraph objects, compares them with 7,168 comparator objects, and retains matched and discordant cases for inspection. A fixed `1e-12` numerical tolerance removed 207 spurious objects caused by floating-point residue without changing any of the 7,086 matched objects. The state-contract compiler drives directional states and transition boundaries; preprocessing, object identity, measurements, comparisons, and interpretation remain explicit study logic.

- [Study, recorded results, and rerun instructions](https://github.com/featuregraph/featuregraph/blob/main/artifacts/studies/bidmc_object_workflow_study.md)
- [Researcher input](https://github.com/featuregraph/featuregraph/blob/main/notebooks/researcher_input/bidmc_researcher_input.ipynb)
- [Generated study](https://github.com/featuregraph/featuregraph/blob/main/notebooks/generated_study/bidmc_generated_study.ipynb)
- [Workflow runner](https://github.com/featuregraph/featuregraph/blob/main/scripts/run_bidmc_researcher_workflow.py)

**What this demonstrates:** translation of an explicit research contract into maintainable computation, cohort-scale execution, provenance, object-level comparison, regression protection, numerical debugging, and failure localization.

**Claim boundary:** the workflow does not establish clinical validity or universal respiratory-object ground truth. The compiler integration is deliberately bounded to the state and event layer.

## Additional evidence of transfer and interoperability

| Engineering question | Current result | Inspect |
| --- | --- | --- |
| Does a frozen construction transfer beyond its development run? | The unchanged TEP reactor-pressure construction reproduced the dominant response across all 10 Fault 2 runs and separated those runs from 10 normal-operation windows on two declared properties. Contrasting faults showed why the result is fault-sensitive, not Fault-2-specific. | [TEP transfer study](https://github.com/featuregraph/featuregraph/blob/main/artifacts/studies/tep_pressure_transfer_study.md) |
| Can FeatureGraph preserve another method's output without taking over detection? | On the 20,700-observation CLaP Crop example, all 16 structural checks passed; object reconstruction reproduced every supplied label exactly and retained nine occurrences, eight relations, and both boundary fragments. | [CLaP interoperability study](https://github.com/featuregraph/featuregraph/blob/main/artifacts/studies/clap_state_object_study.md) |
| Can identical outputs still differ in scientific traceability? | Two paths agreed exactly on sample labels, objects, relations, and measurements, while deterministic contract queries distinguished declared dataset, detector, version, and construction metadata from an output-only surrogate. | [Traceability study](https://github.com/featuregraph/featuregraph/blob/main/artifacts/studies/replica_mechanism_fidelity_study.md) |

## System and software evidence

- [Public package repository](https://github.com/featuregraph/featuregraph): compiler, behavioral representations, study runners, tests, and research records.
- [Research repository](https://github.com/featuregraph/featuregraph-research): released beta, reproducibility manifest, maintained research tracks, and archived software record.
- [Immutable beta release](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0b1) and [archived record](https://doi.org/10.5281/zenodo.21984186).
- [Documentation](https://featuregraph.readthedocs.io/) and [project site](https://featuregraph.ai/).

## The research-engineering pattern

Across these studies, the recurring contribution is not a domain-specific detector. It is the engineering layer that makes a scientific construction explicit and testable:

1. preserve source data, boundaries, exclusions, and external labels;
2. declare states, events, identities, measurements, relations, and limits;
3. compile the deterministic portion into inspectable tables and provenance;
4. validate reconstruction, invariants, joins, transfer, and failure cases;
5. keep unsupported scientific interpretation outside the execution layer.

This is the strongest current evidence that FeatureGraph can carry exploratory research into a reproducible, inspectable computational workflow without hiding uncertainty or silently expanding the claim.
