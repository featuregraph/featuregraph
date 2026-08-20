# Output agreement is not mechanism fidelity

**Status:** completed bounded research record

**Run date:** August 20, 2026

**Executable study:** [`scripts/run_replica_mechanism_fidelity_study.py`](../../scripts/run_replica_mechanism_fidelity_study.py)

## Question

Can two computational results agree at the observation, object, relation, and
measurement levels while differing in whether their scientific origin and
construction contract are inspectable?

This question is motivated by Falck et al., *Training AI Scientists to
Replicate Research*. Their Replica judge distinguishes visual agreement and
claim reproduction from implementation fidelity and scientific integrity. The
paper reports that coding agents can generate plausible results without
faithfully implementing the mechanism an experiment is meant to test.

This study does not reproduce the Replica benchmark or evaluate Faraday. It
uses the existing FeatureGraph-CLaP interoperability study to test one narrower
claim: exact output agreement is insufficient to establish a traceable
scientific construction.

## Construction

The documented CLaP `Crop` example is executed with
`AgglomerativeCLaPDetection` from ClaSPy 0.2.8. Its inferred state sequence and
the original 20,700 observations are materialized twice with
`featuregraph.from_state_sequence`:

1. **Declared CLaP construction.** Dataset, detector, detector version, and a
   study-specific object specification identifier are supplied.
2. **Output-only surrogate.** The identical signal and inferred labels are
   supplied through the same compiler contract, but the source dataset,
   detector, detector version, and study-specific specification identifier are
   omitted. FeatureGraph therefore retains its explicit provenance defaults:
   `unknown`, `external`, `unknown`, and the generic categorical-state
   specification.

Because the labels and signal are identical, this is not a comparison of two
state detectors. It is a controlled comparison between an output with declared
scientific traceability and the same output without those declarations.

## Result

Both paths produced nine state-occurrence objects and eight adjacent-object
relations from 20,700 observations.

| Output-level check | Equal? |
| --- | :---: |
| Reconstructed sample labels | Yes |
| Object boundaries, labels, and sample counts | Yes |
| Adjacent-object relations | Yes |
| Signal measurements | Yes |

An evaluator restricted to the returned state sequence, an equivalent plot,
object boundaries, relations, or summary measurements could not distinguish
the two paths.

The declared scientific contract did distinguish them:

| Traceability query | Declared CLaP | Output-only surrogate |
| --- | :---: | :---: |
| Dataset declared | Pass | Fail |
| Detector declared | Pass | Fail |
| Detector software version declared | Pass | Fail |
| Study-specific construction contract declared | Pass | Fail |

The executable record independently reruns CLaP, verifies the frozen
20,700-label fingerprint, and asserts all four output equivalence checks, all
four declared-construction checks, and all four output-only failures.

## Relation to Replica's evaluation dimensions

| Replica dimension | What this study shows | What it does not show |
| --- | --- | --- |
| Visual fidelity | Identical labels can support identical visual output | No visual score is computed |
| Claim reproduction | Output agreement alone cannot identify the construction that supports a claim | No scientific claim from a Replica task is reproduced |
| Implementation fidelity | Missing detector and contract declarations are queryable despite exact output agreement | Declared metadata does not prove that an external detector actually ran |
| Compute use | Not evaluated | No compute-efficiency claim |
| Scientific integrity | The record does not silently treat unknown provenance as CLaP provenance | The study does not judge an agent's intentions or full research trajectory |

## Supported conclusion

For this CLaP example, exact agreement at the sample, object, relation, and
measurement levels does not imply equal scientific traceability. FeatureGraph
can preserve this distinction as a deterministic contract query rather than
requiring an evaluator to infer it from a plot or final array.

This is evidence for a possible object-layer contribution to agent-generated
research: a judge can query whether a result declares the source method and
construction contract before considering stronger questions about fidelity.

## Important limitation

FeatureGraph records declared provenance; it does not cryptographically prove
that the declared detector produced arbitrary supplied labels. This bounded
runner now independently re-executes CLaP and verifies contract and label
fingerprints, which makes this particular result reproducible but does not
prevent a dishonest process from attaching false metadata elsewhere. Stronger
mechanism verification would require signed lineage or independently controlled
execution.

Accordingly, this study demonstrates detection of *missing* scientific
traceability, not proof of mechanism fidelity and not automated scientific
validation.

## Sources

- Damon Falck et al. *Training AI Scientists to Replicate Research*.
  <https://arxiv.org/abs/2608.13331>
- Arik Ermshaus, Patrick Schäfer, and Ulf Leser. *CLaP - State Detection from
  Time Series*. <https://arxiv.org/abs/2504.01783>
- Existing FeatureGraph interoperability record:
  [`clap_state_object_study.md`](clap_state_object_study.md)
