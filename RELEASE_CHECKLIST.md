# Alpha release record

This file records the completed FeatureGraph alpha release and the checks that should remain true while its maintenance branch evolves.

## Released artifact

| Field | Value |
| --- | --- |
| Package version | `0.1.0a1` |
| Git tag | [`v0.1.0a1`](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0a1) |
| Release date | 2026-07-24 |
| Maintenance branch | `alpha/v0.1.x` |
| Zenodo DOI | [10.5281/zenodo.21535661](https://doi.org/10.5281/zenodo.21535661) |
| Supported Python | 3.10–3.13 |

The tag is the immutable software release. The maintenance branch contains its living oscillation/accumulation research line, documentation, and compatible corrections. The `main` branch contains unreleased successor architecture work.

## Release contents

- explicit oscillation objects;
- wave-derived accumulation objects;
- inspectable construction features and object tables;
- deterministic object queries;
- BIDMC and Tennessee Eastman dataset loaders;
- a versioned reproduction manifest and artifact generator;
- environment, timing, and checksum metadata;
- tests across Python 3.10 through 3.13;
- source and wheel build checks;
- citation and archival metadata.

## Research-line scope

The alpha branch may add datasets, cross-domain demonstrations, evaluation methods, generated evidence, and compatible corrections that exercise the existing oscillation/accumulation workflow. Architectural redesign and incompatible APIs belong on `main`.

## Maintenance verification

Before merging a change into `alpha/v0.1.x`:

- [ ] Confirm the change preserves alpha scope and does not import successor-only behavior from `main`.
- [ ] Run `python -m pytest`.
- [ ] Run `python -m build`.
- [ ] Confirm the clean wheel imports as version `0.1.0a1`.
- [ ] Execute the demonstration notebook when public API examples change.
- [ ] Run `python scripts/reproduce.py --refresh` when datasets, constructors, measurements, or paper evidence change.
- [ ] Compare regenerated tables and figures with the manuscript claims.
- [ ] Review `environment.json` and `run_metadata.json`.
- [ ] Confirm documentation builds without warnings.
- [ ] Update `CHANGELOG.md` when a user-visible correction is introduced.

## Research record

The alpha manuscript and supporting evidence live under [`artifacts/paper/`](artifacts/paper/README.md). The reproduction inputs and expected outputs are defined in [`reproducibility/manifest.json`](reproducibility/manifest.json). Instructions are in [`docs/reproducibility.md`](docs/reproducibility.md).
