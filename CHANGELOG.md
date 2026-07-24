# Changelog

All notable changes to FeatureGraph are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/featuregraph/featuregraph/compare/v0.1.0a1...HEAD
[0.1.0a1]: https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0a1
