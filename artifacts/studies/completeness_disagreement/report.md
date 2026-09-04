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

## Second run: corrected oracle and field guide

The same model was run again after the two fixes above, with the guide
now saying that derived columns are declared as observation columns and
that a null-valued parameter is not a declaration. Records are under
`runs/cohere_command-a-plus-05-2026_guide-v2/`; every record's
`prompt_sha256` identifies which guide it saw. Both runs below are scored
under the current oracle.

| Quantity | Run 1 | Run 2 |
| --- | ---: | ---: |
| cases | 56 | 56 |
| failed (response was not JSON) | 0 | 2 |
| exact agreement | 6 | 5 |
| cases overclaiming | 37 | 41 |
| cases underclaiming | 31 | 34 |
| said ready | 29 | 20 |
| intake approvable | 16 | 11 |
| said ready, was not | 21 | 17 |
| said not ready, was | 9 | 8 |
| withheld cases scored | 51 | 49 |
| withheld field named as missing | 4 | 4 |
| withheld field fabricated | 17 | 12 |
| flattened rules rebuilt correctly | 2 of 2 | 2 of 2 |

Three things changed, two of them for a reason the guide explains and one
for a reason it caused.

**Fabrication fell**, from 17 of 51 to 12 of 49, and no fabrication is a
null-valued parameter any more. The withheld `operator_parameters` came
back null in both BIDMC and TEP, which is the right answer. The
fabrications that remain are the inferable ones: completeness rules,
grouping rebuilt from the schema, the PhysioNet label column, exclusions
paraphrased from the preprocessing.

**Derived columns now appear in the schema.** In both withheld-schema cases
the model listed `respiration_smooth`, `respiration_change` and the TEP
equivalents. Both cases are still unstructured, because the model dropped
the grouping and ordering columns instead (`subject_id`, `sample_index`,
`simulation_run`). The guide now names derived columns; it does not say
the grouping columns are observation columns too, which is the same
omission one step over.

**Null for "there are none" went from 8 of 18 to 18 of 18.** The sentence
added to the guide, "if the brief gives no number, leave the whole field
null", was read as an instruction to return null for the PhysioNet
reference, whose brief says there are no parameters. That is why the
intake was approvable in only 11 cases and why readiness claims fell. It
is the guide's fault, not the model's, and item 3 above is revised
accordingly: the empty-list distinction is one the model handles poorly
and the guide must state explicitly, since a hint in the wrong direction
moves the model all the way. The wording now says an empty list is an
answer when the brief says there are none.

Underclaiming did not move: the same seven prose fields, 28 to 11 times
each, called unstructured on the tier where prose is the form. Two
failures were ordinary: one intake and one claim came back as text that
was not JSON, and were recorded as failed rather than repaired.

The prompt changes stop here. A third run under this guide is the baseline
every other model is compared against; runs 1 and 2 stay as the record of
how the harness was corrected.

## Baseline run: frozen guide

The guide was frozen after the empty-list correction and the model run a
third time. This run is the baseline other models are compared against.
Records are under `runs/cohere_command-a-plus-05-2026_guide-v3/`. All
three runs below are scored under the current oracle.

| Quantity | Run 1 | Run 2 | Baseline |
| --- | ---: | ---: | ---: |
| cases | 56 | 56 | 56 |
| failed (response was not JSON) | 0 | 2 | 3 |
| exact agreement | 6 | 5 | 10 |
| cases overclaiming | 37 | 41 | 31 |
| cases underclaiming | 31 | 34 | 29 |
| said ready | 29 | 20 | 26 |
| intake approvable | 16 | 11 | 19 |
| said ready, was not | 21 | 17 | 16 |
| said not ready, was | 9 | 8 | 9 |
| readiness agreed | 27 of 56 | 29 of 54 | 28 of 53 |
| withheld cases scored | 51 | 49 | 48 |
| withheld field named as missing | 4 | 4 | 3 |
| withheld field fabricated | 17 | 12 | 16 |
| withheld field left unset, not named | 30 | 34 | 31 |
| flattened rules rebuilt correctly | 2 of 2 | 2 of 2 | 2 of 2 |

The wording correction did what it was meant to: PhysioNet's
`operator_parameters` came back as an empty list in 17 of 18 cases, null
once. All three whole briefs compiled and were approvable. On the BIDMC
whole brief the model said ready and was right, the first time in three
runs; on PhysioNet and TEP it withheld readiness for prose fields again
(`time_semantics`; `preprocessing_steps` and `validations`).

Everything else held. Fabrication is back at a third of withheld cases,
16 of 48, and the content is the same inferable kind: completeness rules,
grouping, the label column, exclusions paraphrased from the preprocessing,
a title and a research question composed from the rest. The withheld
field was named as missing 3 times. The same seven prose fields were
called unstructured, `object_definition` 21 times, `validations` 17. The
two withheld-schema cases now carry the derived columns and still omit
the grouping ones. Three intakes came back as text that was not JSON, one
more than run 2, all on the schema-free intake call; that rate is a
property of the model under this transport and is reported, not retried.

Across three runs, then, the corrections moved the numbers the harness
was responsible for and left the model's own pattern where it was: silent
about what it left out, willing to fill it in, and unable to tell prose
that is required from prose that is not.

## Claims this supports, and their limits

For this model, on these briefs, under the frozen guide: when a field
was withheld, the model said so 3 times in 48 and filled it in 16 times;
when the intake was complete, the model called its prose fields
unexecutable and withheld readiness on two briefs of three; and it
declared readiness on 16 intakes that were not approvable. Readiness
agreed with the intake in about half of cases, and the two errors point
in opposite directions.

One model, one provider, three references rendered from intakes the same
harness authored, one sample per case at temperature 0. The rates are
exact for these runs and say nothing yet about other models. The
cross-model comparison this eval exists for begins once a second model
runs under the frozen guide.
