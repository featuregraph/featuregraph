# Separating model proposals from execution

A technical case study for infrastructure and agent-reliability teams.

## Summary

FeatureGraph is a deterministic compiler for researcher-declared structure over
time-series data. In the conversational study builder, a Cohere Command model
proposes candidate study contracts; it cannot approve or execute one. Execution
consumes only a contract that has passed deterministic validation and whose
fingerprint has been re-verified from disk. No model call occurs during
execution.

That separation is not a policy statement or a system-prompt instruction. It is
enforced by three checks in code, each of which fails loudly and specifically.
This document states the architecture precisely, shows where it is implemented,
and gives two recorded instances where it stopped a run that would otherwise
have produced a plausible but wrong result.

## The boundary

### Propose — non-deterministic, no authority

`ResearchAssistant` is a protocol with two methods, `draft` and `revise`. Its
docstring states the constraint directly: *"Propose a revision without granting
execution authority."*

The Cohere implementation calls `cohere.ClientV2(api_key=...).chat(...)` at
`temperature=0` with a JSON-schema-constrained `response_format`, and validates
the returned payload against the schema with `Draft202012Validator` before it
travels any further. Its system prompt instructs the model to *"Separate
researcher authority from model proposals. Never approve, execute, infer stress,
claim causality, or assign scientific validity."*

The proposer is swappable. `OfflineResearchAssistant` implements the same
protocol with frozen responses and no network, and the demo runs end-to-end
against it. Nothing downstream of `propose` knows or cares which proposer ran.

Every proposal records its own provenance: model name, Cohere SDK version, and
SHA-256 fingerprints of the prompt, the response text, the request schema, and
the transport schema. The model interaction is itself an auditable artifact.

### Validate — deterministic, specific on failure

`compile_states(observations, contract)` compiles a declarative contract against
a DataFrame and checks two properties over the resulting state masks:

- **Exclusive** — no observation is in two states at once.
- **Exhaustive** — no observation is in no state at all.

Failure is not a generic error. The compiler raises with the offending
positions:

```
States overlap at observation indices [3, 4, 5].
No state is active at observation indices [88, 89].
```

It also returns a `validation_report` table — one row per check, with pass/fail
and details — alongside the compiled observations, so a caller can inspect what
passed rather than only what failed.

### Execute — no model calls, fingerprint-gated

Approval is a separate, deliberately hostile step. `approve_study_contract()`
refuses any candidate that arrives carrying its own `approval` block. Its
docstring gives the reason: *"This prevents a model or other authoring helper
from granting itself execution authority."* It also refuses a candidate with any
failed validation result, and refuses one with unresolved questions still open.

Approval stamps a SHA-256 over the canonical JSON of every field except the
approval record itself — excluded because it stores the fingerprint of the
remainder and would otherwise be self-referential.

The run path then does something worth noting: it writes the approved contract
to disk and **reads it back through `load_approved_study_contract()`**, which
recomputes the fingerprint and refuses to load on mismatch, before handing the
loaded object to the executor. Execution therefore consumes a re-verified
artifact, not the in-memory object that approval produced.

`StudyExecutor` is a protocol with exactly two methods — `validate(candidate)`
and `run(approved_contract, run_directory)`. It has no Cohere-specific types in
its signature.

Finally, materialization self-checks. `from_state_sequence()` reconstructs the
original label sequence from the objects it just built and raises if the
reconstruction is not exact:

```
Occurrence objects did not reconstruct the state sequence.
```

## Two recorded instances where the boundary held

Both are drawn from study records published before this document, not
constructed for it.

### A held-out run stopped rather than substituting a column

The BIDMC multiscale cardiac-phase contract was frozen before being applied
unchanged to 49 held-out records. From the study record:

> The first held-out run stopped because at least one record did not contain the
> expected AVR column. The schema-handling logic was corrected so that validation
> used lead V when AVR was unavailable; lead II remained the primary ECG event
> series in every record. No scientific or analytical parameter was changed.

The failure mode this avoids is the common one: silently falling back to an
available column, completing the run, and reporting a number nobody can trace
back to a substitution. The distinction that matters for a reliability claim is
that the *schema handling* was corrected while the *scientific contract* stayed
frozen — and the fingerprint makes that distinction checkable rather than
asserted.

### An undeclared boundary was left undeclared

In the PhysioNet wearable-protocol dataset, the authors' notebook narrative
describes 12 version-1 tags, while every downloaded version-1 `tags.csv`
contains 13. The notebook's task-span code references only the first 12 marks
and leaves the final mark uninterpreted.

FeatureGraph followed the executable declaration and assigned no meaning to the
extra mark. Time not named by the source protocol was materialized as
`unassigned` rather than absorbed into an adjacent stage — 3,642 of 23,398
compiled seconds (15.6%) in version 1, and 461 of 34,817 seconds (1.3%) in
version 2.

That 15.6% is the result. Treating every gap between button presses as part of
the neighbouring task or rest stage would have produced a tidier dataset by
inventing meaning the source never declared.

## Evidence base

| Study | Result | Scale |
| --- | --- | --- |
| PhysioNet wearable protocol | 248 of 248 occurrences preserved both declared boundaries exactly; 248 of 248 joined to source self-report; 99 of 99 compiler checks passed | 33 eligible participants, two protocol versions |
| BIDMC object workflow | 7,926 complete objects against 7,168 comparator objects; 7,086 matched; a fixed 1e-12 tolerance removed 207 spurious objects without changing any matched object | 53 public records |
| CLaP interoperability | 16 of 16 structural checks passed; reconstruction reproduced every supplied label exactly | 20,700 observations |
| TEP transfer | A frozen construction reproduced the dominant response across all 10 Fault 2 runs and separated them from 10 normal-operation windows | 20 runs |

Archived record: [10.5281/zenodo.21984186](https://doi.org/10.5281/zenodo.21984186)

## What is not claimed

- No claim that model proposals are correct. The architecture assumes they are
  not, and makes acceptance conditional on deterministic checks.
- No claim of clinical validity, causality, or physiological ground truth in any
  study cited above. Each study record carries its own explicit claim boundary.
- No claim of multi-tenant isolation. This describes a single-partner pilot;
  isolation between multiple calling organisations is a deliberate later
  decision, not a solved problem.
- The exclusive/exhaustive checks verify that a contract is internally coherent
  against supplied data. They do not verify that it is scientifically
  appropriate. That judgement stays with the researcher, which is why approval
  requires a named authority.

## Interface direction

The `validate` and `execute` steps are the reusable surface, and they are
already vendor-neutral at the type level — `StudyExecutor` names no proposer
type. Exposing them as callable tools requires repackaging, not redesign:

- `validate_contract(contract)` → pass, or a structured failure naming the
  offending indices
- `execute_contract(fingerprint)` → objects, validation report, provenance

`propose_contract` deliberately stays outside that surface. A lab bringing its
own model to the proposal step is a lower-friction integration than routing that
step through someone else's infrastructure, and the protocol boundary already
supports it.

## Verifying this

Everything above is in this repository, MIT-licensed:

- `src/featuregraph/study_builder/conversation.py` — proposer and executor
  protocols, the Cohere client, `approve_and_run`
- `src/featuregraph/contracts/state_contract.py` — the compiler and its checks
- `src/featuregraph/contracts/study_contract.py` — approval, fingerprinting,
  fingerprint-verified loading
- `src/featuregraph/behaviors/state_occurrence.py` — materialization and its
  reconstruction self-check
- `apps/conversational_study_demo/` — runnable demo, including an `--offline`
  network-free mode
- `tests/test_conversational_study_demo.py` — tests over the loop

```bash
python -m pip install -e ".[dev,study-builder]"
python -m scripts.run_conversational_study_demo --offline --open
```

The offline mode runs the full path with no API key and no network, against a
protected fixture.
