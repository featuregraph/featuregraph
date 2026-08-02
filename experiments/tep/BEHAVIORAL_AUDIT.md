# Tennessee Eastman behavioral audit

This audit evaluates the FeatureGraph representation without fitting a fault
classifier. It consumes the complete reactor-pressure oscillation objects from
`experiments.tep.compare_faults` and performs three analyses.

1. **Regime characterization** compares early and sustained post-injection
   objects with pre-injection objects from the same simulation run. It records
   median changes and signed Cliff's delta for each intrinsic property.
2. **Cross-run reproducibility** measures whether each change has the same
   direction across the five independent runs. A change is marked repeatable
   when at least 80% of runs agree and the absolute median Cliff's delta is at
   least 0.33.
3. **Query audit** executes ten deterministic questions against the object and
   audit tables. The resulting catalog demonstrates the behavioral information
   exposed without reconstructing states or boundaries from raw samples.

An object-coverage table records every fault/run/regime combination, including
combinations with zero complete objects. This prevents a failed or incomplete
construction from being mistaken for an uneventful regime.

Run the prerequisite object construction and the audit:

```bash
python -m experiments.tep.compare_faults \
  --faults 1 2 4 6 7 12 14 \
  --output-dir artifacts/tep/fault_comparison

python -m experiments.tep.behavioral_audit \
  --objects artifacts/tep/fault_comparison/objects.csv \
  --output-dir artifacts/tep/behavioral_audit
```

The audit is descriptive. Its repeatability threshold is an explicit reporting
rule rather than a learned decision boundary or claim of statistical
significance. Only complete reactor-pressure oscillation objects are included.

## Figures

Generate the review figures after constructing the comparison and audit artifacts:

```bash
python -m experiments.tep.visualize_behavioral_audit
```

This writes SVG and PNG versions to
`artifacts/tep/behavioral_audit/figures/`:

- `amplitude_by_regime`: object-amplitude distributions across regimes.
- `cross_run_effect_sizes`: signed effect sizes and repeatability by fault.
- `object_boundary_reconstruction`: a FeatureGraph start/peak/end reconstruction
  around the known injection. It is explicitly not a raw pressure trace.
- `behavioral_signature_heatmap`: the strongest signed behavioral properties
  for each fault and regime.

The committed SVG files are lightweight review artifacts. PNG files can be
regenerated locally when raster output is needed.

