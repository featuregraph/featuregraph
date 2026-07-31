# Reproducibility guide

> **Alpha provenance:** Published FeatureGraph results and archived artifacts were produced with `v0.1.0a1`. The `main` branch contains an incompatible, unreleased redesign. Do not use `main` to regenerate or overwrite alpha evidence.

## Reproduce the released alpha

Clone the immutable tag:

```bash
git clone --branch v0.1.0a1 --depth 1   https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/reproduce.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

The maintained alpha branch [`alpha/v0.1.x`](https://github.com/featuregraph/featuregraph/tree/alpha/v0.1.x) is suitable for alpha-compatible work, but the tag is the authority for exact reproduction.

## Fixed data

| Dataset | Fixed selection | Source |
| --- | --- | --- |
| BIDMC PPG and Respiration Dataset | Subject 1, version 1.0.0 | PhysioNet |
| Tennessee Eastman | Mode 1, fault 1, simulation run 1 | `mv-per/tennessee-eastman-dataset` |

The alpha script caches source data outside the repository and records inputs, environment details, timing, and checksums. See the [tagged reproducibility guide](https://github.com/featuregraph/featuregraph/blob/v0.1.0a1/docs/reproducibility.md) for the exact cache paths, output inventory, and release procedure.

## Evaluation artifacts

The synthetic evaluation notebook and generated files under `artifacts/paper/evaluation/` are alpha-generation evidence. Their provenance must identify:

- FeatureGraph release `v0.1.0a1`;
- API generation `alpha`;
- the compatible release tag rather than current `main`.

A future evaluation of the successor architecture must use a separate artifact set and must not silently replace these results.

## Development validation

Tests and notebooks on `main` validate the changing successor architecture, not alpha reproducibility. Their results should be labeled development-only until a new release freezes the replacement API.
