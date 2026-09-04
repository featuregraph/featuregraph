# Completeness disagreement, first run: Cohere command-a-plus-05-2026

One model, 56 cases, none failed. The model's account of what it left out
disagreed with the intake's own on 49 of them.

- Model: `command-a-plus-05-2026`, temperature 0, one sample per case.
- Framework: commit `d006955` (main after PR #88); intake call sent as a
  bare JSON request, claim call with schema, both validated locally.
- Records: `runs/cohere_command-a-plus-05-2026/cases/`, one JSON per case
  with the brief digest, the intake, the claim, both provenance records and
  the score. `cases.csv`, `fields.csv`, `withheld.csv` and `summary.json`
  are derived from them by `scripts/summarize_completeness_run.py`.

## Headline

| Quantity | Count |
| --- | ---: |
| cases | 56 |
| exact agreement between claim and intake | 7 |
| cases where the model overclaimed | 35 |
| cases where the model underclaimed | 31 |
| cases where the model said nothing was outstanding | 24 |
| model said ready | 29 |
| intake was approvable | 18 |
| said ready, was not | 20 |
| said not ready, was | 9 |

Readiness agreed in 27 of 56 cases. The two errors run in opposite
directions and have different causes, below.

## Withheld fields: silence, then fabrication

Fifty-one briefs each omitted one field. The right answer is to leave it
null and name it.

| Outcome | Count |
| --- | ---: |
| left unset and named as missing | 4 |
| left unset and not named | 30 |
| declared anyway (fabricated) | 17 |
| declared anyway and named as missing | 0 |

By reference: BIDMC 5 of 17 fabricated and none named; TEP 8 of 17
fabricated and none named; PhysioNet 4 of 17 fabricated and 4 named. The
four named cases are all PhysioNet: `title`, `observation_schema`,
`operator_parameters`, `exclusions`.

Sixteen of the seventeen fabrications carry content; one is an empty list
for `validations`, which the intake reads as "there are none". Most of the
content is inferable from the rest of the brief, which is what makes it
easy to produce and hard to notice: `completeness_rules` filled in as
exclusive and exhaustive in both BIDMC and TEP; `grouping_and_order`
rebuilt from the schema and the time column; `states_or_labels` for
PhysioNet set to the `protocol_state` column the schema mentions; a
`research_question` and a `title` for TEP written from the measurements.
Two fabrications are half-answers the intake should not have accepted:
`operator_parameters` for BIDMC and TEP came back as the parameter named in
the state rules with `value: null`. The intake's shape check requires a
`value` key and does not require it to be non-null, so a named parameter
with no value passed as declared. That is a gap in the oracle, not the
model, and is recorded under *What the run found about the harness*.

## Underclaiming: prose called unstructured

The model named 118 declared, correctly shaped fields as outstanding across
31 cases, 117 of them on the approvable tier. Every one was reported as
`believed_unstructured`, none as missing.

| Field | Times called unstructured |
| --- | ---: |
| object_definition | 28 |
| validations | 23 |
| time_semantics | 17 |
| preprocessing_steps | 16 |
| claim_limits | 14 |
| provenance | 10 |
| measurements | 8 |

These are text and list fields whose required form *is* prose. The model
applied "prose is not executable" where no rule expression is asked for.
In 14 cases this was the only disagreement. It is also why the model
refused readiness on both compilable whole briefs: BIDMC's full brief came
back complete and approvable, and the model said not ready because
`object_definition`, `measurements`, `validations` and
`preprocessing_steps` were prose; TEP's full brief, the same, for
`object_definition` alone.

## Overclaiming: what the model did not say

Forty field-instances across 35 cases where a field was unset or
unstructured and the model did not name it:

| Source | Count |
| --- | ---: |
| withheld field left unset, not named | 30 |
| `operator_parameters` returned null where the brief said there are none (PhysioNet) | 7 |
| `observation_schema` fabricated without the derived columns the states use | 2 |
| `exclusions` returned null where the brief declared them | 1 |

The PhysioNet row is worth its own line. That reference supplies labels in
a column and so declares `operator_parameters` as an empty list, which the
brief renders as "None; there are none." In 8 of the 18 PhysioNet cases the
model returned null for it. Null and empty list are the two answers the
intake schema was rebuilt to keep apart, because v1 wrote the same thing
for both; the model collapses them the way v1 did.

## Shape: the flattened rules were rebuilt

Two briefs gave the state rules as sentences with no notation. In both the
model returned correct `{"op": ..., "left": ..., "right": ...}` expressions
and the intake compiled. No shape blindness arose from flattening.

The two shape-blind cases are the `observation_schema` withheld briefs. The
model fabricated a schema from context, omitted the derived columns
(`respiration_change`, `reactor_pressure_rate` and their parents), and the
states then referenced columns the schema never declared. The intake
reports that as `observation_schema` unstructured; the model called the
intake complete. Whether a derived column belongs in the observation schema
is a design question about the v1 emission path, recorded below, so these
two cases should be read with that in mind.

## What the run found about the harness

Three things the eval turned up about its own oracle and briefs. The
first two were fixed after this run and before any second model:

1. `operator_parameters` accepted `{"name": ..., "value": null}` as
   declared, because only the key was required. A null value is now
   refused as not answered. Two fabrications in this run are of that form.
2. The v1 contract the intake emits has no `derive` section, so columns a
   study derives must be listed in `observation_schema` for the state rules
   to reference them. The briefs list them there, and the model was not
   told why. The field guide now says so, and says a null-valued parameter
   is not a declaration.
3. "None; there are none." is the rendering of an empty list. It is
   correct, and the model still returned null for it in 8 of 18 cases. The
   rendering stays; the finding is the model's.

Scoring is pure and every record keeps the intake and the claim, so the
run can be re-scored under the corrected oracle without a model call:
`scripts/summarize_completeness_run.py RUN --rescore`. Under it, the two
null-valued parameters count as unstructured and the model's silence about
them as shape blindness, which moves four headline numbers: exact
agreement 7 to 6, cases overclaiming 35 to 37, shape-blind cases 2 to 4,
and false ready 20 to 21. The tables committed beside the records are the
scores as recorded at run time. The field-guide change cannot be applied
retroactively, since it alters the prompt; that needs the rerun.

## Claims this supports, and their limits

For this model, on these briefs: when a field was withheld, the model said
so 4 times in 51 and filled it in 17 times; when the intake was complete,
the model called its prose fields unexecutable and withheld readiness; and
it declared readiness on 20 intakes that were not approvable. Readiness
agreed with the intake in under half of cases.

One model, one provider, three references rendered from intakes the same
harness authored, one sample per case at temperature 0. The rates are
exact for this run and say nothing yet about other models. The
cross-model comparison this eval exists for begins with the second run.
