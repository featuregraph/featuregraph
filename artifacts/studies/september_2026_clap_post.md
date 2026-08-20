# FeatureGraph Study of the Month: September 2026

## Publication status

Prepared draft. Do not imply review, collaboration, or endorsement by the CLaP
authors. Author contact is separate from public publication.

## LinkedIn post

For September's FeatureGraph Study of the Month, I looked at what happens when
the scientific states come from another method.

CLaP detects recurring states in a time series. FeatureGraph does not replace
that detector or reinterpret its output. Instead, this study asks whether the
state sequence produced by CLaP can cross a software boundary without losing
its labels, temporal occurrences, boundaries, or provenance.

The new deterministic state-contract compiler preserved all 20,700 supplied
labels and derived nine state occurrences with explicit entry and exit events.
Those occurrences were then materialized as queryable FeatureGraph objects and
adjacency relations. Reconstructing the original CLaP sequence from the objects
produced an exact match.

This is an interoperability result, not a claim that FeatureGraph detected or
improved the states. The deterministic checks establish structural preservation;
whether the detected states are scientifically meaningful remains a research
judgment.

Study record:
https://github.com/featuregraph/featuregraph/blob/main/artifacts/studies/clap_state_object_study.md

CLaP paper: https://arxiv.org/abs/2504.01783

#ScientificComputing #TimeSeries #ReproducibleResearch #ResearchSoftware

## Publication checklist

- [x] Execute the generated notebook with its declared optional dependencies.
- [x] Confirm all sixteen structural checks and four query checks pass.
- [x] Confirm the displayed counts and figure match the study record.
- [x] Verify the CLaP paper and maintained implementation links.
- [x] Keep publication independent of author outreach and avoid implying endorsement.
