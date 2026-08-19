# Source-draft archive

This archive collects the paper-writing material found across the three FeatureGraph repositories and the relevant core-repository refs on August 19, 2026. The website repository contained no paper drafts.

## Full-manuscript lineages

| Archived file | Original repository and ref | Original path | Status |
| --- | --- | --- | --- |
| `frozen_releases/v0.1.0a2_bidmc_manuscript.md` | `featuregraph/featuregraph@v0.1.0a2` | `artifacts/paper/bidmc_llm_preservation_study/manuscript.md` | Early alpha manuscript; 3,465 words |
| `frozen_releases/alpha_v0.1.x_bidmc_manuscript.md` | `featuregraph/featuregraph@alpha/v0.1.x` | same | Frozen preservation manuscript; 7,765 words |
| `frozen_releases/beta_v0.1.x_bidmc_manuscript.md` | `featuregraph/featuregraph@beta/v0.1.x` | same | Frozen representation/transfer manuscript; 8,138 words |
| `main_framework/researcher_workflow_draft.md` | `featuregraph/featuregraph@main` | `artifacts/paper/framework/researcher_workflow_draft.md` | Main-branch workflow draft; primary base for the master |
| `main_framework/featuregraph_framework_draft.md` | `featuregraph/featuregraph@main` | `artifacts/paper/framework/featuregraph_framework_draft.md` | Short cross-domain framework draft |

The `v0.1.0b1` BIDMC manuscript is byte-identical to the archived `alpha/v0.1.x` manuscript (Git blob `91b23663d21c197823c3e7b6edd4775d3956cac5`) and is therefore represented by that one copy. Agent branches that repeated frozen paper trees were also omitted when their blobs were identical.

## Supporting drafts

- `main_framework/framework.md` records the transition-centered implementation discussion.
- `main_framework/study_results.md` records the corrected current BIDMC execution totals and numerical-boundary fix.
- `research_repository/markdown_sections/` preserves the editable component-paper structure from `featuregraph/featuregraph-research@main`.

The research repository's LaTeX tree was not copied because it is a second rendering of the same section manuscript and would create two apparent authorities. The original remains unchanged in `featuregraph/featuregraph-research`.

## Consolidation decisions

1. The master paper is a framework paper, not a rewritten alpha or beta release paper.
2. Current BIDMC workflow results and frozen release results are separate study records.
3. TEP supports cross-domain representation and controlled transfer, not a claim that reactor pressure alone identifies Fault 2.
4. Historical source copies should not be edited. Corrections belong in the master with an explicit provenance note.
