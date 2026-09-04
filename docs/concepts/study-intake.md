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
  no contract can be emitted at all. Ordering counts as declared whether it
  names a sort column or places observations on a constructed timeline — the
  second fixes order at least as firmly and names no column, and treating it
  as an omission was a bug.

`approvable`
: the research question, the object definition, the measurements, the
  exclusions, the claim limits, and the rest. The compiler never reads them.
  A person putting their name to a study should have.

A third state exists that the flat list could not express: a field answered in
a form the compiler cannot execute. It is not missing — someone answered — but
it cannot compile. A study contract may declare its completeness requirements
in its own vocabulary rather than as the compiler's `exclusive` and
`exhaustive` flags; that is a declaration, not a gap.
{py:attr}`~featuregraph.study_builder.intake.StudyIntake.unstructured` reports
these separately, and the error raised on compilation names the two causes
apart:

```python
intake.to_state_contract()
# IntakeIncompleteError: This intake cannot compile yet -- not yet declared:
# observation_schema; declared without structure: completeness_rules.
```

## Who said it

Every declared field records its source: the researcher, or a model
proposing on their behalf. `declare` states; `propose` proposes; `confirm`
is the researcher adopting a proposal, and it is the only way a proposal
becomes a declaration.

```python
intake = StudyIntake.empty().propose(research_question="Does pressure rise?")
intake.missing_information      # research_question is not missing
intake.proposed                 # ('research_question',)
intake.is_complete              # may be True
intake.is_approvable            # False until confirmed
intake.confirm("research_question").is_approvable
```

A proposal compiles like any declared field. It is not missing, and it is
not unstructured. What it is not is the researcher's word: the checkpoint
renders it with "(proposed by the assistant, not yet confirmed)", the
study candidate lists it under `unresolved_questions`, and the approval gate
refuses it. In the conversation, the researcher's approval is the
confirmation, and the approved specification records which fields were
adopted that way rather than stated.

This exists because of a measurement. Asked to declare an intake from a
brief with one field removed, a general model filled the gap with a
plausible answer about a third of the time and, asked afterwards what it had
left out, said nothing. A plausible answer nobody gave is the one nothing
downstream catches. The intake cannot stop a model from writing it; it can
refuse to let it count as declared until a person says so.

Payloads written before sources existed load with every field attributed to
the researcher. A payload that is what a model returned loads with
`from_payload(payload, source="model")`, and every field is a proposal.

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
contract, for instance, carries sixteen of the seventeen. The one it leaves
unstated is the research question, which lives in the paper rather than in a
construction contract.

```{note}
An earlier version of this reader looked only at `study`, `dataset`,
`state_compiler`, `measurements` and `validations`, and reported that same
contract as carrying **ten** of seventeen. It never opened `sources`, where the
contract declares its signals, its timeline frequency and its interval closure.

That is the failure mode worth naming, because it is quiet and it is
defamatory: a reader that does not look somewhere does not return a smaller
answer, it returns a false one — and the false answer accuses a researcher of
never having written down something they did write down. The fix is that the
reader now reads every section these contracts use; the guard is
`test_session_intake_is_seeded_from_the_template_contract`, which asserts the
signals are found and that exactly one field is outstanding.
```

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

### What confirmation settles

The demo session asks one construction question and reads the answer for
assent. An affirmative answer clears the assistant's unresolved questions,
which is right: a researcher outranks a hedging model on the question they were
asked. It used to do two further things that it should not have.

It replaced the assistant's proposed statistics with a module-level list on
every confirmation, so an assistant that named two of them silently got five,
and the specification a researcher approved was not the one they had been
shown. It now leaves a proposal alone.

And when the assistant named none, it filled them in from that same constant —
a default standing in for an answer. It now inherits what the template contract
already declares, and records that it did so in the candidate's provenance. If
the template declares none either, the field stays empty and the intake reports
it as a hole.

Questions settled by a confirmation are written to provenance as
`questions_settled_by_confirmation` rather than dropped. The researcher's answer
outranks the hedge; the hedge is still part of how the candidate came to exist.
