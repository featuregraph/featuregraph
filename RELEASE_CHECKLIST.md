# Release checklist: 0.2.0b1

Use this checklist for the first archived release of the compiler lineage on
`main`. The 0.1 releases on `alpha/v0.1.x` and `beta/v0.1.x` are unaffected.

## Before tagging

- [ ] Merge the release-preparation pull request after all required CI jobs pass.
- [ ] Confirm `python -m pip install .` succeeds in a clean environment.
- [ ] Confirm `featuregraph.__version__`, `pyproject.toml`, `docs/conf.py` and
      the CI wheel check all read `0.2.0b1`.
- [ ] Re-run `scripts/run_bidmc_multiscale_heldout.py` at the release commit
      where PhysioNet is reachable and confirm `subject_summary.csv` is
      byte-identical to the committed file. This is the provenance the held-out
      report does not record on its own.
- [ ] Run `scripts/verify_derived_contracts.py --dataset all` at the release
      commit and confirm 53 of 53 and 10 of 10 identical.
- [ ] Confirm the README and docs name `v0.2.0b1` where they name a release.

## Tag and release

- [ ] Create annotated tag `v0.2.0b1` from the verified commit and push it.
- [ ] Create the GitHub prerelease for the tag; copy the `0.2.0b1` changelog
      entry into the release notes.
- [ ] Attach the wheel and source distribution from the CI build artifacts.

## Archive and citation

- [ ] Confirm the Zenodo–GitHub integration is enabled for this repository and
      note which all-versions record it will publish under.
- [ ] Publish the release and wait for Zenodo ingestion.
- [ ] Verify the archived files include `artifacts/studies`, `artifacts/contracts`
      and `artifacts/paper/master`.
- [ ] Replace the all-versions DOI in `CITATION.cff` with the version DOI, and
      cite that version DOI in the BIDMC preprint (reference 9).
- [ ] Record the release commit SHA, the release URL, the all-versions DOI and
      the version DOI in the preprint's availability section.
