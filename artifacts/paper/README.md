# FeatureGraph alpha paper

The standalone BIDMC analysis-preservation study is maintained in
[`bidmc_llm_preservation_study/manuscript.md`](bidmc_llm_preservation_study/manuscript.md).
It records the blinded LLM comparison, the original absolute-threshold cohort,
and the subsequent MAD-normalized cohort as a separate research paper draft.
The draft now also contains a primary-source related-work section, a formal
development-versus-transfer protocol, categorized threats to validity, and an
AI-use disclosure linked to the experiment-level provenance record.

This directory is the canonical manuscript and evidence workspace for the released FeatureGraph alpha. Paper-specific edits belong on `alpha/v0.1.x`, not on `main`.

## Manuscript order

1. [Abstract and conclusion](abstract_and_conclusion/abstract_and_conclusion.md) — the current summary and closing claims; split into separate submission sections when the target venue is selected.
2. [Introduction](introduction/introduction.md)
3. [Framework](framework/framework.md)
4. [Alpha implementation](alpha_implementation/alpha_implementation.md)
5. [Evaluation methods](evaluation_methods/evaluation_methods.md)
6. [Results](results/results.md)
7. [Cross-domain demonstrations](cross_domain_demonstrations/cross_domain_demonstrations.md)
8. [Discussion and limitations](discussion_and_limitations/discussion_and_limitations.md)

The numbered list records reading order. The files remain separate so each section can be revised and reviewed independently.

## Evidence and generated artifacts

- `tables/` contains generated object tables used to inspect and report alpha behavior.
- `figures/` contains generated and evaluation figures.
- `environment.json` records the software and hardware environment used for a reproduction run.
- `run_metadata.json` records dataset selections, execution metadata, and artifact checksums.

Files in the manuscript section directories are authored source. Tables, figures, and run metadata produced by `scripts/reproduce.py` are generated evidence and should not be edited by hand.

## Reproduce the evidence

From the repository root:

```bash
python -m pip install -e ".[dev]"
python scripts/reproduce.py
```

The script reads [the versioned manifest](../../reproducibility/manifest.json) and writes the expected evidence into this directory. Full instructions, data provenance, and verification steps are in [the reproducibility guide](../../docs/reproducibility.md).

## Revision discipline

When changing a manuscript claim:

1. identify the table, figure, test, or source passage supporting it;
2. regenerate affected evidence when construction parameters or measurements change;
3. distinguish demonstrated results from proposed future capabilities;
4. keep limitations visible where the corresponding result is interpreted;
5. record substantive changes in a focused `paper:` commit.

The frozen study authority is
[`v0.1.0a2`](https://github.com/featuregraph/featuregraph/tree/v0.1.0a2),
archived at [Zenodo](https://doi.org/10.5281/zenodo.21939319). This branch may
extend the paper and research record without moving the tag. Architectural
redesign and transition-only successor claims belong on `main` or a new alpha
line rather than being retroactively attributed to the frozen release.
