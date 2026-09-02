# Study intake

The conversational Study Builder collects a study one answer at a time. Until
recently it collected those answers into an object of its own — an intake JSON —
which somebody then transcribed by hand into a compiler contract. Two objects,
no link between them, and nothing that could tell you whether the second
followed from the first.

`featuregraph.study_builder.intake` removes the second object. A
{py:class}`~featuregraph.study_builder.intake.StudyIntake` *is* a study
contract, with the fields that nobody has answered yet left unset. Filling it in
is not a step before writing a contract; it is writing the contract.

## Missing information is derived

The intake's list of open questions is computed from which fields are unset:

```python
from featuregraph.study_builder import StudyIntake

intake = StudyIntake.empty().declare(title="Tank fill regime")
intake.missing_information
# ('boundary_rules', 'claim_limits', ..., 'validations')
```

Nothing stores that list, and no model asserts it. The previous schema kept
`missing_information` in the payload, written by the same assistant that was
filling the fields in — so the record of what was still unknown was only as
reliable as the thing it was auditing. A payload that claims to be complete is
recomputed on load and told otherwise.

## Unset, and declared as none

`preprocessing_steps: []` used to mean "nobody has said." It now means "the
researcher has said there is no preprocessing," which is a finding, not a gap.
Only `None` means unanswered.

Payloads marked `schema_version: 1` are still read the old way — `[]` and
`"Not yet specified"` both count as unset — so an existing checkpoint loads
without being reinterpreted.

## Two kinds of incomplete

A study can be missing things the compiler needs, or things a reviewer needs.
These are tracked separately, because they lead to different conversations:

`compilable`
: `observation_schema`, `grouping_and_order`, `states_or_labels`,
  `operator_parameters`, `boundary_rules`, `completeness_rules`. Without these
  no contract can be emitted at all.

`approvable`
: the research question, the object definition, the measurements, the
  exclusions, the claim limits, and the rest. The compiler never reads them.
  A person putting their name to a study should have.

A third state exists that the flat list could not express: a field answered in
prose where the compiler needs a rule. It is not missing — someone answered —
but it cannot execute. {py:attr}`~featuregraph.study_builder.intake.StudyIntake.unstructured`
reports these separately, and the error raised on compilation names the two
causes apart:

```python
intake.to_state_contract()
# IntakeIncompleteError: This intake cannot compile yet -- not yet declared:
# observation_schema; declared without structure: completeness_rules.
```

## What it emits

{py:meth}`~featuregraph.study_builder.intake.StudyIntake.to_state_contract`
returns a `state-contract-v1` mapping that
{py:func}`~featuregraph.contracts.compile_states` accepts as-is. Before
returning it, the intake checks that every column and parameter the state rules
name was actually declared — so a typo surfaces during intake rather than after
a dataset fetch.

{py:meth}`~featuregraph.study_builder.intake.StudyIntake.to_study_candidate`
returns an approval-free payload for
{py:func}`~featuregraph.contracts.approve_study_contract`, with every remaining
hole written into `unresolved_questions`. No new enforcement was added for this:
refusing to approve a candidate with unresolved questions is a rule that already
existed. An incomplete intake is unapprovable because it is honest about being
incomplete.

The candidate never carries an `approval` key. Approval is granted by a named
person calling `approve_study_contract`, and by nothing else.

## The checkpoint is a view

{py:func}`~featuregraph.study_builder.intake.render_checkpoint` produces the
markdown summary a researcher reads between turns. It is rendered from the
intake rather than written by the assistant, which means the summary on screen
and the payload the compiler would receive can no longer disagree.

## In the conversation

{py:class}`~featuregraph.study_builder.ConversationalStudySession` holds a live
intake. It is seeded from the template contract by
{py:func}`~featuregraph.study_builder.intake.intake_from_study_contract`, so the
fields a published study already declares are not asked again, and the fields it
never wrote down are visible instead of assumed. The PhysioNet wearable protocol
contract, for instance, carries ten of the seventeen; it states no research
question, no observation schema, and no ordering column for its grouping.

Every proposal the assistant makes is recorded as a declaration on that intake
rather than written straight into a candidate. The candidate's
`unresolved_questions` are then the model's own questions *plus* the holes
derived from the intake, over the fields this session is answerable for —
`governed_intake_fields`, by default the research question and the measurements.

That last part is the point of the wiring. `unresolved_questions` used to come
straight from the model, which meant an assistant that left a hole and did not
notice it produced a candidate that looked complete. Now a hole in a governed
field blocks approval whether or not the model mentioned it:

```python
session.state()["open_questions"]
# ['measurements: The statistics computed over those objects.']
```

Fields outside `governed_intake_fields` are still reported — they appear in
`session.state()["intake"]` and in the conversation checkpoint — but they do not
block a study whose template already declares them.

The intake is rendered into the conversation checkpoint that is written every
turn, not into a file of its own. It changes on every turn, and a per-turn
artifact for it would be one more thing to keep in step.
