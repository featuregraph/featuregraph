# Changelog

All notable changes to FeatureGraph are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and Python package versions follow [PEP 440](https://peps.python.org/pep-0440/).

## [Unreleased]

## [0.1.0b1] - 2026-08-17

### Added

- Grouped rolling-maximum/rolling-mean BIDMC respiration envelope with raw
  signal preservation and an explicit offline-versus-causal timing contract.
- Interval-valued flat extrema, midpoint projections, and ambiguity flags for
  degenerate trough–peak–trough constructions.
- A 53-subject post hoc transfer audit with saved object, annotation,
  ambiguity, and detector-discordance tables.
- A stable `detector_discordant_episodes.csv` handoff schema that labels
  isolated episodes and bursts while leaving clinical interpretation
  explicitly unassigned.
- Regression tests for grouped smoothing, plateau midpoint conventions,
  event-count preservation, ambiguity invalidation, raw excursion, and cohort
  accounting invariants.
- Causal FeatureGraph observation encoders and a paired-seed DQN experiment for
  raw, raw-history, behavioral-only, and augmented CartPole/MountainCar states.
- Reproducible, cached MountainCar trajectories generated from the canonical
  dynamics with a seeded exploratory momentum policy and RL transition schema.
- Deterministic, cached CartPole trajectories for oscillation and accumulation
  research, including provenance metadata and an end-to-end behavioral-object
  integration test.
- Canonical paper index and revision guidance.
- CI execution of the public demonstration notebook.
- Tests for manifest-driven reproduction.

### Changed

- Promoted the maintained oscillation/accumulation research implementation to
  beta status after deterministic full-cohort validation.
- Moved SciPy out of the installed core dependency set; it remains an optional
  development/notebook dependency for reproducing the frozen LLM comparator.
- Updated the BIDMC notebook and manuscript to distinguish detector agreement,
  discordant-episode localization, and clinical interpretation.
- Defined `alpha/v0.1.x` as the maintained oscillation-and-accumulation
  research line while keeping successor architecture work on `main`.
- Pinned the Tennessee Eastman source revision and made its cache
  revision-specific.
- Made the reproduction script read and validate the versioned manifest.
- Focused the README on installation, documentation, and research resources.
- Completed DOI metadata for the frozen alpha record.
- Consolidated repository ignore rules.

### Fixed

- Distinguished transition anchors from the midpoint convention used for
  extended extrema by point-based comparators.
- Excluded overlapping extremum intervals from complete-object metrics instead
  of silently retaining structurally ambiguous cycles.

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

### Fixed

- Assigned peaks and troughs to the preceding sample at directional reversals.
- Derived complete oscillation boundaries from explicit trough–peak–trough extrema.
- Preserved flat regions inside extrema-defined object boundaries.
- Propagated parent oscillation completeness to accumulation summaries.
- Plotted the smoothed reactor-temperature signal used to construct Eastman boundaries.
- Corrected corrupted arrow and em-dash characters in the README.

[Unreleased]: https://github.com/featuregraph/featuregraph/compare/v0.1.0b1...HEAD
[0.1.0b1]: https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0b1
[0.1.0a1]: https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0a1
