# Cohere-assisted Study Builder prototype

This directory contains an experimental authoring workflow for a broader
FeatureGraph study contract. Cohere proposes clarification questions and a
schema-valid draft. A researcher reviews the draft, and deterministic local
checks decide whether it is eligible for approval. The language model never
executes the scientific study.

Use the notebooks in order:

1. [`00_cohere_assisted_contract.ipynb`](00_cohere_assisted_contract.ipynb)
   profiles a synthetic file bundle, asks clarification questions, and drafts a
   broad authoring contract.
2. [`01_review_and_execute_physionet_contract.ipynb`](01_review_and_execute_physionet_contract.ipynb)
   constrains an executable PhysioNet payload, exposes every difference,
   requires explicit approval, and reproduces the protected cohort result.

## Setup

From the repository root:

```bash
python -m pip install -e ".[dev,notebooks,study-builder]"
export COHERE_API_KEY="your-key"
python -m jupyterlab notebooks/study_builder/00_cohere_assisted_contract.ipynb
```

The notebook runs without an API key by using a frozen example response. To
make a live Cohere request, set `RUN_COHERE = True` in the configuration cell;
your Cohere account's usage and rate limits apply.

The fixture resembles the completed PhysioNet wearable study but contains no
source or participant data, so this authoring notebook stops before execution.
The review-and-execute notebook then uses the same payload consumed by the
[`physionet-wearable-study-v1` contract](../../artifacts/studies/physionet_wearable/study_contract.json)
and the [deterministic runner](../../scripts/run_physionet_wearable_protocol_study.py).
A network-free protected test reconstructs all 33 eligible participants, 248
declared occurrences, and 99 compiler checks from the approved contract.

## Conversational interface

The bounded browser demonstration in
[`apps/conversational_study_demo`](../../apps/conversational_study_demo) wraps
this authoring and execution boundary in a small chat interface. It writes a
Markdown conversation checkpoint, presents the candidate specification for
explicit approval, runs the protected PhysioNet workflow, and supports a
versioned measurement revision. See its README for the three-minute script.

To open the complete vertical slice directly:

```bash
python -m jupyterlab notebooks/study_builder/01_review_and_execute_physionet_contract.ipynb
```

Leave `RESEARCHER_APPROVES = False` until the candidate, difference table, and
validation table have been inspected. An unapproved candidate is never passed
to the runner.
