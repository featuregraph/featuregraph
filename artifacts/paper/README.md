# FeatureGraph paper workspace

## Authoritative draft

[The BIDMC arXiv draft](master/featuregraph_master_draft.md) is the only
editable paper on `main`. It reports the 53-record BIDMC respiratory-object
study, the concentration and annotation disposition of 840 FeatureGraph-only
objects, the numerical-boundary correction, and the bounded deterministic
compiler integration.

The studies remain available as shorter evidence records:

1. [BIDMC object workflow](../studies/bidmc_object_workflow_study.md)
2. [TEP pressure transfer](../studies/tep_pressure_transfer_study.md)
3. [CLaP interoperability](../studies/clap_state_object_study.md)

## Released papers

The master draft is intentionally distinct from frozen release manuscripts.
Use the immutable [`v0.1.0b1` release](https://github.com/featuregraph/featuregraph/tree/v0.1.0b1)
and its [Zenodo archive](https://doi.org/10.5281/zenodo.21984186) for the citable
beta result. The [`beta/v0.1.x`](https://github.com/featuregraph/featuregraph/tree/beta/v0.1.x)
branch is the compatible research line; `alpha/v0.1.x` remains frozen for
historical links.

## Editing rule

Edit the master draft for the current BIDMC paper. TEP, CLaP, PhysioNet, and
other FeatureGraph studies remain separate research records and should not be
added to this manuscript merely to broaden the framework claim. Do not copy
frozen manuscripts or superseded component drafts back into `main`. When
results differ across versions, identify the repository ref, construction, and
run rather than averaging or silently replacing values. Git history preserves
the component drafts removed during consolidation.
