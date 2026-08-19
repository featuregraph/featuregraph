# FeatureGraph paper workspace

This directory is the publication workspace on `main`.

## Authoritative draft

[`master/featuregraph_master_draft.md`](master/featuregraph_master_draft.md) is the current master framework paper. It consolidates the main-branch researcher-workflow draft, the BIDMC implementation record, the TEP transfer study, and the reusable framework argument.

The master draft is intentionally distinct from the frozen alpha and beta manuscripts. It describes the current framework and workflow on `main`; it does not rewrite released implementation history or combine incompatible result totals.

## Source drafts

[`source_drafts/`](source_drafts/) contains the drafts used during consolidation:

- exact copies of the three distinct frozen-release BIDMC manuscripts;
- exact copies of the four drafts that previously lived in `artifacts/paper/framework/` on `main`;
- the editable Markdown paper-section bundle from `featuregraph/featuregraph-research`.

See [`source_drafts/README.md`](source_drafts/README.md) for provenance, deduplication, and recommended use.

## Editing rule

Edit the master draft for the current paper. Treat files under `source_drafts/frozen_releases/` as read-only historical records. When a source contains a result that differs from the master, preserve the distinction by repository, ref, construction, and run date rather than averaging or silently replacing values.
