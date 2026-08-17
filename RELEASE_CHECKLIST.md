# Beta release record

This record promotes the maintained FeatureGraph oscillation/accumulation
research line to beta after the full BIDMC envelope and interval-extremum
audit. The immutable alpha releases remain unchanged.

## Released artifact

| Field | Value |
| --- | --- |
| Package version | `0.1.0b1` |
| Git tag | [`v0.1.0b1`](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0b1) |
| Release date | 2026-08-17 |
| Source branch | `alpha/v0.1.x` |
| Frozen predecessor | [`v0.1.0a2`](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0a2) |
| Frozen alpha archive | [10.5281/zenodo.21939319](https://doi.org/10.5281/zenodo.21939319) |
| Supported Python | 3.10–3.13 |

The beta tag is the immutable source release. The branch name is retained to
preserve existing links and the historical separation from the incompatible
successor architecture on `main`.

## Beta scope

The beta supports deterministic offline construction, measurement, ambiguity
detection, comparison, and handoff of explicit behavioral objects. The BIDMC
adapter preserves raw observations, grouped smoothing, transition anchors,
interval-valued extrema, midpoint projections, causal detection latency, and
detector-discordant episodes.

The beta does not claim:

- clinical interpretation or abnormality diagnosis;
- automatic respiratory morphology classification;
- universal detector equivalence;
- real-time operation of the offline-aligned envelope;
- compatibility with the transition-only successor on `main`.

## BIDMC beta evidence

- 53 subjects processed with no failures;
- 8,205 detected FeatureGraph peak events;
- 8,133 complete FeatureGraph objects;
- 7,086 matches to 7,168 frozen comparator objects;
- 1,047 FeatureGraph-only and 82 comparator-only objects;
- 100 explicitly ambiguous rows, including 47 formerly complete objects;
- stable `detector_discordant_episodes.csv` handoff with clinical
  interpretation explicitly unassigned;
- 119 tests passed before the beta release candidate was assembled.

## Release verification

- [x] Confirm the diff remains compatible with the oscillation/accumulation
  research line and contains no successor-only API.
- [x] Run `python -m pytest` (119 passed).
- [x] Run targeted Ruff checks on changed Python files.
- [x] Run `python -m build`.
- [x] Confirm the clean wheel metadata reports version `0.1.0b1` without SciPy
  installed as a core dependency.
- [ ] Execute both public notebooks from the repository root.
- [x] Regenerate the 53-subject envelope/plateau result directory.
- [x] Run `experiments/bidmc_llm_capture/verify_beta_release.py`.
- [x] Compare regenerated tables with the manuscript claims.
- [ ] Confirm GitHub Actions passes on Python 3.10–3.13, notebook execution,
  and distribution builds.
- [ ] Create and verify the immutable `v0.1.0b1` prerelease.

## Reproduction

The beta-specific contract is recorded in
`experiments/bidmc_llm_capture/BETA_MANIFEST.json`. The existing general paper
artifacts remain governed by `reproducibility/manifest.json` and
`docs/reproducibility.md`.

SciPy is not a core package dependency in the beta. It remains an optional
development/notebook dependency solely for reproducing the frozen LLM-selected
comparison path.
