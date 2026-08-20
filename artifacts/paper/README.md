# FeatureGraph paper workspace

## Authoritative draft

[The master framework draft](master/featuregraph_master_draft.md) is the only
editable paper on `main`. It integrates the paired-notebook workflow with the
BIDMC implementation, the frozen TEP transfer study, and the later CLaP
interoperability result.

The studies remain available as shorter evidence records:

1. [BIDMC object workflow](../studies/bidmc_object_workflow_study.md)
2. [TEP pressure transfer](../studies/tep_pressure_transfer_study.md)
3. [CLaP interoperability](../studies/clap_state_object_study.md)

## Released papers

The master draft is intentionally distinct from frozen release manuscripts.
Use the immutable [`v0.1.0b1` release](https://github.com/featuregraph/featuregraph/tree/v0.1.0b1)
and its [Zenodo archive](https://doi.org/10.5281/zenodo.21984186) for the citable
beta result. The [`beta/v0.1.x` paper](https://github.com/featuregraph/featuregraph/blob/beta/v0.1.x/artifacts/paper/bidmc_llm_preservation_study/manuscript.md)
is the compatible paper line; `alpha/v0.1.x` remains frozen for historical
links.

## Editing rule

Edit the master draft for the current paper. Do not copy frozen manuscripts or
superseded component drafts back into `main`. When results differ across
versions, identify the repository ref, construction, and run rather than
averaging or silently replacing values. Git history preserves the component
drafts removed during consolidation.
