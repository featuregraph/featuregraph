# Completeness disagreement: does a model know what it left out?

An eval of model self-knowledge, not of model capability. A model is given a
researcher's brief and asked to declare a study intake; then it is shown its
own intake and asked which fields it believes are still unset, which it
answered in prose where the compiler needed a rule, and whether the intake
is ready to approve. The intake itself answers the same questions exactly,
by construction: `missing_information` and `unstructured` are derived from
what is declared and are never written by a model. The model's answer is
scored against that.

Ground truth costs nothing and needs no annotator: it is a set difference
computed by the compiler.

## What is measured

| Quantity | Meaning |
| --- | --- |
| overclaimed | a field is unset or unstructured and the model did not say so |
| underclaimed | the model called a declared, shaped field missing |
| shape blind | an unstructured field the model called complete; wrong twice |
| fabricated | a field the brief withheld that the model declared anyway |
| false ready | the model said the intake was ready; the intake says otherwise |

Shape blindness exists only on the compilable tier, the six fields with a
shape check. Overclaiming and underclaiming are reported per tier.

## Cases

`reference/` holds three complete, compilable, approvable intakes written as
eval fixtures from the repository's published constructions: the BIDMC
respiration envelope, the Tennessee Eastman reactor-pressure rate, and the
PhysioNet wearable protocol study. They are fixtures, not published
contracts, and carry no approval.

Each reference yields one brief rendered as prose, one brief per field with
that field withheld, and one brief per compilable rule field with the rule
rendered as a sentence and no notation. The withheld cases give a second
ground truth the intake cannot: the harness knows what was left out, so a
declared value for it is a fabrication. The flattened cases are where shape
blindness is expected to appear.

## Running

```bash
python -m scripts.completeness_disagreement --provider offline
ANTHROPIC_API_KEY=... python -m scripts.completeness_disagreement \
    --provider anthropic --model claude-opus-5
COHERE_API_KEY=... python -m scripts.completeness_disagreement \
    --provider cohere --model command-a-plus-05-2026
```

The offline provider declares nothing and says so; it is the floor of the
eval and the test fixture. Each run writes `cases.csv`, one row per case,
and `cases/<case>.json` with the intake, the claim, both provenance records
and the score, under `outputs/completeness_disagreement/<model>/`.

A model's claim is stored in each record under `claim` and is marked
`"authoritative": false`. It never enters an intake and gates nothing.

## What is not here yet

No model has been run. Results, when they exist, belong in a `report.md`
beside this file with the per-case CSVs copied in, following the other
studies. The Anthropic adapter deliberately configures no server-side
fallback: a refusal rerun on another model would attribute that model's
answer to the one named, so a refusal is recorded as a failed case.
