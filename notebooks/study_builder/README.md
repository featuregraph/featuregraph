# Cohere-assisted Study Builder prototype

This directory contains an experimental authoring workflow for a broader
FeatureGraph study contract. Cohere proposes clarification questions and a
schema-valid draft. A researcher reviews the draft, and deterministic local
checks decide whether it is eligible for approval. The language model never
executes the scientific study.

Start with [`00_cohere_assisted_contract.ipynb`](00_cohere_assisted_contract.ipynb).

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
source or participant data. The first protected product test is to reproduce
the maintained 33-participant, 248-occurrence result from an approved contract;
this notebook stops before that execution step.
