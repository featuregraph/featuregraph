# Reproducibility guide

This document describes how to recreate and extend the FeatureGraph alpha research artifacts from a clean checkout.

## Supported environment

FeatureGraph supports CPython 3.10, 3.11, 3.12, and 3.13. CI tests those versions on Ubuntu. Runtime and development dependencies are bounded in `pyproject.toml`; each reproduction run records the exact installed environment.

```bash
git clone --branch alpha/v0.1.x --single-branch \
  https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Versioned inputs

[`reproducibility/manifest.json`](../reproducibility/manifest.json) is the authority for the random seed, fixed dataset selections, immutable source revisions, and expected outputs. The reproduction script reads this file rather than maintaining a second set of hard-coded selections.

| Dataset | Fixed selection | Source authority |
| --- | --- | --- |
| BIDMC PPG and Respiration Dataset | Subject 1, version 1.0.0 | Versioned PhysioNet release |
| Tennessee Eastman | Mode 1, fault 1, simulation run 1 | Pinned commit in `mv-per/tennessee-eastman-dataset` |

BIDMC files are cached beneath `~/.cache/featuregraph/bidmc/1.0.0`. Tennessee Eastman files are downloaded from the pinned Git revision and cached beneath a revision-specific directory in `~/.cache/featuregraph/tennessee_eastman/`. Data files are not committed to this repository.

Use `--refresh` to redownload source files.

## Regenerate tables and figures

```bash
python scripts/reproduce.py
```

Artifacts are written to `artifacts/paper` by default. To use another directory:

```bash
python scripts/reproduce.py --output-dir path/to/output
```

The script:

1. validates the manifest schema;
2. loads its fixed dataset selections;
3. verifies that the Tennessee Eastman loader uses the declared revision;
4. constructs oscillation and accumulation object tables;
5. generates annotated figures;
6. records the environment, source metadata, timing, and manifest checksum;
7. fails if any manifest-declared output is missing.

CSV contents are deterministic for the same data, code, and parameters. PNG metadata and wall-clock timing can vary by platform.

## Randomness

The manifest currently declares seed 1729. Alpha constructors and queries are deterministic and do not depend on randomness; Python and NumPy are nevertheless seeded so future research preprocessing cannot silently introduce nondeterminism.

## Verification

Before merging a change that affects alpha behavior or evidence:

```bash
python -m pytest
python -m build
python scripts/reproduce.py --refresh
```

CI also:

- tests Python 3.10 through 3.13;
- builds the source distribution and wheel;
- smoke-tests the installed wheel;
- executes the public alpha demonstration notebook;
- checks the reproduction command;
- provides a manual full-reproduction job that uploads generated evidence.

## Extending the alpha research line

The alpha remains active as an oscillation-and-accumulation research line. A new dataset belongs here when it can exercise the existing construction workflow without requiring a successor architecture.

For each new dataset:

1. state why its behavior is meaningfully oscillatory, accumulative, or both;
2. choose a stable public source and pin a version, revision, and fixed selection;
3. add a narrow loader that records source provenance;
4. register the selection and expected outputs in the manifest;
5. apply the existing alpha constructors before introducing domain-specific exceptions;
6. add tests for grouping, boundaries, completeness, and deterministic summaries;
7. compare object schemas and measurements with the existing domains;
8. document failures, parameter sensitivity, and unsuitable cases alongside successful results;
9. connect every paper claim to generated evidence.

New datasets, evaluations, and compatible corrections are in scope. Redesigning the behavioral object architecture or importing successor-only APIs from `main` is not.

## Archived release

The immutable software release is [`v0.1.0a1`](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0a1). Its archived research record is [10.5281/zenodo.21535661](https://doi.org/10.5281/zenodo.21535661). The maintenance branch may extend the research record, but results must continue to identify the exact code revision and dataset manifest used.
