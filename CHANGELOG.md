# Changelog

All notable changes to FeatureGraph are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and Python package versions follow [PEP 440](https://peps.python.org/pep-0440/).

## [Unreleased]

## [0.2.0b1] - 2026-09-03

First release of the compiler lineage. `main` shares no history with the
`alpha/v0.1.x` and `beta/v0.1.x` branches, and this release is not
API-compatible with any 0.1 release. The 0.1 releases remain the authority for
the results they archived; nothing here regenerates them.

### Added

- `compile_states`, a deterministic compiler from a declarative state contract
  to states, occurrences with identity, and boundary events, with exclusive
  and exhaustive validation and structured refusals carrying a stable code
  and locus.
- `state-contract-v2`: a `derive` section so a construction can carry its own
  rolling windows, shifts, differences and arithmetic inside the fingerprinted
  contract, and a `missing_policy` of `exclude` that keeps undefined edge
  observations outside the partition and reports them. `state-contract-v1` is
  frozen and refuses everything v2 added.
- Study contracts with canonical SHA-256 fingerprints, researcher approval
  that refuses a candidate carrying its own approval record, and load-time
  re-verification before execution.
- `StudyIntake`, a study contract with holes in it, and the bounded
  conversational study builder over it, with a Cohere proposer and an offline
  proposer sharing one protocol.
- The public assistant application under `apps/assistant`, with per-session
  and global call budgets.
- `featuregraph.shape`: occurrence tables, rise/fall asymmetry and occurrence
  drift, measures that read compiled output and nothing else.
- Dataset loaders for BIDMC (with a pinned manifest of 53 file digests, an
  offline mode and a shared cache), Tennessee Eastman, a synthetic pulse and
  a synthetic tank fill.
- Frozen study records under `artifacts/studies`: the BIDMC multiscale
  held-out study across 53 subjects, the subject 13 multiscale case, the
  BIDMC object workflow, the CLaP state-object study, the PhysioNet wearable
  protocol and NORI interoperability studies, the Tennessee Eastman pressure
  transfer study and the replica mechanism fidelity study.
- The BIDMC and Tennessee Eastman constructions expressed entirely as v2
  contracts under `artifacts/contracts`, with `scripts/verify_derived_contracts.py`
  recording row-by-row equivalence with the published preprocess-then-compile
  path: 53 of 53 BIDMC subjects and 10 of 10 Fault 2 runs identical.
- The BIDMC preprint draft and figures under `artifacts/paper/master`.

### Changed

- The package version is now `0.2.0b1`. `main` had reported `0.1.0a1` since
  the lineages diverged, so every provenance stamp written from `main` before
  this release carries that string; treat it as "unreleased compiler
  lineage" rather than as the alpha.
- `CITATION.cff` now names this release and its Zenodo version DOI,
  [10.5281/zenodo.22286856](https://doi.org/10.5281/zenodo.22286856), under
  the all-versions record 10.5281/zenodo.21939317.

### Migration

There is no migration path from the 0.1 object API. A 0.1 construction is
re-expressed as a state contract; the two verified contracts under
`artifacts/contracts` are the worked examples.

## [0.1.0a1] - 2026-07-24

### Added

- Alpha implementation of explicit oscillation objects.
- Wave-derived accumulation objects with parent completeness propagation.
- Inspectable construction features and object tables.
- Deterministic query interface.
- BIDMC and Tennessee Eastman dataset loaders.
- Reproducibility script and manifest for paper tables and figures.
- Environment and hardware capture for benchmark runs.
- Data-download and archival-release documentation.
- Citation and Zenodo metadata.
- CI tests across Python 3.10 through 3.13.
- Package-build, clean-wheel-install, and reproduction smoke checks.
- Archival release on Zenodo with [version DOI 10.5281/zenodo.21535662](https://doi.org/10.5281/zenodo.21535662).

### Fixed

- Assigned peaks and troughs to the preceding sample at directional reversals.
- Derived complete oscillation boundaries from explicit trough–peak–trough extrema.
- Preserved flat regions inside extrema-defined object boundaries.
- Propagated parent oscillation completeness to accumulation summaries.
- Plotted the smoothed reactor-temperature signal used to construct Eastman boundaries.
- Corrected corrupted arrow and em-dash characters in the README.

[Unreleased]: https://github.com/featuregraph/featuregraph/compare/v0.2.0b1...HEAD
[0.2.0b1]: https://github.com/featuregraph/featuregraph/releases/tag/v0.2.0b1
[0.1.0a1]: https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0a1
