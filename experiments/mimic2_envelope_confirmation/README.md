# MIMIC-II envelope/plateau confirmation

This experiment applies the frozen BIDMC envelope and plateau constructions to
20 deterministically selected, non-BIDMC subjects from the public MIMIC-II
Matched Waveform Database.

Read `PROTOCOL.md` before running the experiment. The protocol distinguishes
comparator-transfer confirmation from clinical breath validation.

Run from the repository root:

```bash
PYTHONPATH=src:. python \
  experiments/mimic2_envelope_confirmation/run_confirmation.py
```

HTTP responses are cached outside the results directory. Generated result
tables are written to `results/mimic2_envelope_confirmation/`.
