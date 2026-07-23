# Alpha release checklist

Use this checklist for the archival alpha release.

## Repository

- [ ] Merge the reproducibility pull request after all required CI jobs pass.
- [ ] Confirm `python -m pip install .` succeeds in a clean environment.
- [ ] Confirm the supported Python matrix is 3.10 through 3.13.
- [ ] Confirm runtime and development dependencies remain bounded.
- [ ] Run `python scripts/reproduce.py --refresh`.
- [ ] Compare regenerated tables and figures with the submission copy.
- [ ] Review `environment.json` and `run_metadata.json`.
- [ ] Confirm README text renders without mojibake.

## Version and release

- [ ] Confirm package version and `featuregraph.__version__` are both `0.1.0`.
- [ ] Create annotated tag `v0.1.0` from the verified commit.
- [ ] Push the tag and create the corresponding GitHub release.
- [ ] Copy the `0.1.0` changelog entry into the release notes.

## Archive and citation

- [ ] Enable GitHub archiving for this repository in Zenodo.
- [ ] Publish the GitHub release and wait for Zenodo ingestion.
- [ ] Verify the archived files and metadata.
- [ ] Add the Zenodo DOI to `CITATION.cff`, `.zenodo.json`, and README.
- [ ] Create a small metadata-only follow-up release if the DOI update must itself be archived.

## Submission record

- [ ] Record the release commit SHA.
- [ ] Record the GitHub release URL.
- [ ] Record the Zenodo concept DOI and version DOI.
- [ ] Record the operating system and hardware used for any reported benchmarks.
- [ ] Archive the exact generated tables, figures, environment record, and run metadata used in the paper.
