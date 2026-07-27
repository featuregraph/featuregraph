# FeatureGraph 0.2.0b1 release checklist

## Semantics and API

- [x] Transition, Oscillation, and Accumulation semantics are authoritative.
- [x] Public constructors and object schemas are documented.
- [x] Parent identity and completeness are explicit.
- [x] Irregular time and non-default indexes have defined behavior.
- [x] Alpha-to-beta migration is documented.

## Validation

- [x] Unit and integration tests cover groups, multiple signals, missing
  values, flat regions, partial objects, smoothing, sensitivity, composition,
  timestamps, indexes, and deterministic identity.
- [x] Held-out FeatureGraph and SciPy comparison uses disjoint tuning and test
  seeds.
- [x] Confidence intervals, boundary overlap, measurement errors, and
  high-noise degradation are reported.
- [ ] CI is green on Python 3.10–3.13 for the release commit.

## Demonstration and reproducibility

- [x] The end-to-end notebook demonstrates Transition → Oscillation →
  Accumulation → Query.
- [x] Every notebook executes against the beta environment.
- [x] BIDMC and Tennessee Eastman artifacts regenerate from the candidate.
- [x] Evaluation artifacts and checksums regenerate from the beta candidate.

## Packaging

- [x] Package and runtime version are `0.2.0b1`.
- [x] Package maturity classifier is Beta.
- [x] Source distribution and wheel build successfully.
- [x] The wheel installs in a clean environment and imports Transition.
- [x] Changelog, citation, archive metadata, and candidate website are
  synchronized.

## External release actions

- [ ] Merge the verified beta pull request.
- [ ] Tag the verified merge commit `v0.2.0b1`.
- [ ] Create a GitHub prerelease and attach distributions and checksums.
- [ ] Publish the corresponding Zenodo version.
- [ ] Record the new version DOI without changing the concept DOI.
- [ ] Verify the public website, GitHub release, DOI, and installation command.
