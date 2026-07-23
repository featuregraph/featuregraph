# Reproducibility guide

This document describes how to recreate the FeatureGraph paper artifacts from a clean checkout.

## Supported environment

FeatureGraph supports CPython 3.10, 3.11, 3.12, and 3.13 on Linux, macOS, and Windows. CI tests the supported Python versions on Ubuntu. Runtime and development dependencies are bounded in `pyproject.toml`; the exact installed environment is recorded by the reproduction script.

Create an isolated environment and install the package:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Data

The script downloads only the runs used by the demonstration:

| Dataset | Fixed selection | Source |
| --- | --- | --- |
| BIDMC PPG and Respiration Dataset | Subject 1, version 1.0.0 | PhysioNet |
| Tennessee Eastman | Mode 1, fault 1, simulation run 1 | `mv-per/tennessee-eastman-dataset` |

BIDMC files are downloaded from `https://physionet.org/files/bidmc/1.0.0/bidmc_csv/` and cached beneath `~/.cache/featuregraph/bidmc/1.0.0`. Tennessee Eastman files are downloaded through GitHub's Git LFS media endpoint and cached beneath `~/.cache/featuregraph/tennessee_eastman`. Data files are not committed to this repository.

Use `--refresh` to redownload source files. The run metadata records the dataset selections, source-file paths, seed, and artifact checksums. The manifest at `reproducibility/manifest.json` is the authority for fixed inputs and expected outputs.

## Regenerate tables and figures

Run:

```bash
python scripts/reproduce.py
```

Artifacts are written to `artifacts/paper` by default. To choose another location:

```bash
python scripts/reproduce.py --output-dir path/to/output
```

The script creates four complete object tables, two annotated-object figures, `environment.json`, and `run_metadata.json`. Re-running with the same source data and FeatureGraph version produces identical CSV contents. PNG metadata and benchmark timing may vary by platform.

## Randomness

The fixed seed is 1729. The current constructors and queries are deterministic and do not depend on randomness; the seed is nevertheless set for Python and NumPy so future stochastic preprocessing cannot silently make the reproduction path nondeterministic.

## Benchmarks and hardware

The reproduction run records:

- operating system and release;
- architecture and processor string;
- logical CPU count;
- Python implementation and version;
- exact package versions;
- wall-clock time for each dataset pipeline.

These details are stored in `environment.json` and `run_metadata.json`. Wall-clock values are descriptive and should not be compared across machines without matching hardware and software environments.

## Verification

Before a release:

```bash
python -m pytest
python -m build
python scripts/reproduce.py --help
```

CI performs tests on every supported Python version and builds both the source distribution and wheel. A manual `workflow_dispatch` run can execute the network-dependent full reproduction job and upload its artifacts.

## Archival release

1. Merge the release pull request with green CI.
2. Create an annotated `v0.1.0` tag from the verified commit.
3. Create a GitHub release using the matching changelog entry.
4. Enable the repository in Zenodo and publish the GitHub release.
5. Add the resulting DOI to `CITATION.cff`, `.zenodo.json`, and the README.
6. Verify the Zenodo archive contains the source, citation metadata, changelog, manifest, and reproduction instructions.

A DOI cannot be recorded before Zenodo creates it. Do not invent or pre-allocate one in repository metadata.
