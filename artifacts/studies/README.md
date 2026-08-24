# FeatureGraph study guide

The studies form a cumulative research sequence. They do not make the same kind
of claim, and later studies do not replace earlier ones.

## 1. BIDMC: establish the workflow

[BIDMC respiratory-object workflow](bidmc_object_workflow_study.md) is the
complete first implementation of the researcher-input/generated-study pair. It
asks whether a declared signal construction can be expanded across a cohort
while retaining observations, states, events, boundaries, object properties,
discordance, and validation evidence.

- [Researcher input](../../notebooks/researcher_input/bidmc_researcher_input.ipynb)
- [Generated study](../../notebooks/generated_study/bidmc_generated_study.ipynb)
- [Workflow runner](../../scripts/run_bidmc_researcher_workflow.py)
- [Current framework paper](../paper/master/featuregraph_master_draft.md)

## 2. TEP: test frozen transfer

[TEP reactor-pressure transfer](tep_pressure_transfer_study.md) freezes the
construction selected on Fault 2 run 10 and tests it on held-out Fault 2 runs,
normal-operation windows, and contrasting fault classes. The result supports a
repeatable abnormal-pressure representation, not a Fault 2 classifier.

- [Researcher input](../../notebooks/researcher_input/tep_researcher_input.ipynb)
- [Generated study](../../notebooks/generated_study/tep_generated_study.ipynb)
- [Current framework paper](../paper/master/featuregraph_master_draft.md#7-tennessee-eastman-process-transfer-study)

## 3. CLaP: test interoperability

[CLaP state-object interoperability](clap_state_object_study.md) begins with
states detected by an independent method. The state-contract compiler preserves
the external labels and derives occurrence boundaries; the object adapter then
materializes bounded objects and relations without claiming the detector's
scientific role.

This is the prepared **FeatureGraph Study of the Month for September 2026**.

- [Researcher input](../../notebooks/researcher_input/clap_researcher_input.ipynb)
- [Generated study](../../notebooks/generated_study/clap_generated_study.ipynb)
- [Construction figure](clap_crop_object_construction.png)
- [Adapter implementation](../../src/featuregraph/behaviors/state_occurrence.py)
- [State-contract compiler](../../src/featuregraph/contracts/state_contract.py)
- [Focused tests](../../tests/test_state_occurrence.py)

## Reading the evidence

| Study | Primary evaluation | Important limitation |
| --- | --- | --- |
| BIDMC | Comparator matching, annotations, cohort execution, regression checks | Comparator and annotations are reference points, not universal ground truth |
| TEP | Held-out replications, normal windows, contrasting faults | Normal windows share one record; cross-fault evidence uses one run per class |
| CLaP | Exact reconstruction and structural invariants | Evaluates representation of supplied states, not CLaP detection quality |
| PhysioNet wearable protocols | Exact source-boundary preservation, lossless self-report joins, shared schema across protocol versions | Represents the published protocol; does not detect stress or validate physiological biomarkers |

## 4. PhysioNet: preserve a published protocol

[PhysioNet wearable protocol representation](physionet_wearable_protocol_study.md)
begins with the stages, physical button marks, exclusions, and self-reports
published by the dataset authors. FeatureGraph preserves 248 declared protocol
occurrences across 33 eligible participants, retains undeclared gaps as
`unassigned`, and measures native-rate wearable signals without interpreting
them as detected stress.

- [Executable study](../../scripts/run_physionet_wearable_protocol_study.py)
- [Focused tests](../../tests/test_physionet_wearable_protocol_study.py)
- [Source dataset](https://physionet.org/content/wearable-device-dataset/1.0.1/)

## 5. Replica connection: separate output agreement from traceability

[Output agreement is not mechanism fidelity](replica_mechanism_fidelity_study.md)
materializes the same CLaP signal and state sequence through a declared
scientific construction and an output-only surrogate. The two paths agree at
the sample, object, relation, and measurement levels, while deterministic
queries distinguish whether the dataset, detector, software version, and
study-specific contract are declared.

- [Executable study](../../scripts/run_replica_mechanism_fidelity_study.py)
- [Prior CLaP interoperability record](clap_state_object_study.md)
- [Replica paper](https://arxiv.org/abs/2608.13331)

The editable paper authority on `main` is
[the master framework draft](../paper/master/featuregraph_master_draft.md).
Released alpha and beta histories remain authoritative on their frozen refs and
are not duplicated here.
