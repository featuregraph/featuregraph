# Subject 5 hysteresis ablation

## Question

After robust subject-level scaling, subject 5 produced 388 complete candidate
objects. This ablation asks whether those candidates arise because the rising
state repeatedly flickers near one threshold. The entry threshold remains the
subject-1-calibrated normalized value `k = 0.807624`; only the exit threshold
changes. `diff_lag=45` and `max_state_gap=7` remain frozen.

The hysteretic state enters when normalized 45-sample change is greater than
`k`, retains its prior value while change is between the entry and exit
thresholds, and exits at or below the lower threshold. FeatureGraph still does
not infer which transitions are breaths or which peaks matter.

## Result

| Exit threshold | Complete objects | Mean period | Ann1 matched | Ann2 matched |
| ---: | ---: | ---: | ---: | ---: |
| `1.00k` | 388 | 1.229 s | 15 | 24 |
| `0.75k` | 384 | 1.241 s | 15 | 24 |
| `0.50k` | 377 | 1.263 s | 15 | 24 |
| `0.25k` | 369 | 1.290 s | 15 | 24 |
| `0.00k` | 365 | 1.304 s | 15 | 24 |

Lowering the exit threshold reduces the count by only 23 objects (5.9%). It
does not increase the number of annotation matches, reduce missed annotations,
or improve median peak error. Even the widest tested neutral band leaves 341
to 350 detected candidates unmatched, depending on annotator.

## Interpretation

Hysteresis works as an explicit persistence rule, but it does not repair the
subject 5 segmentation. Most false candidates are not brief interruptions
inside the neutral band. The normalized difference crosses the entry
threshold again after a genuine exit, so a lower exit threshold can merge only
a small fraction of them.

This narrows the next test. The construction needs a rule governing repeated
entries—such as a physiologically agnostic minimum object duration, minimum
separation between accepted peaks, or a prominence-like transition contract—
not further exit-threshold tuning. Any such rule should be declared on a
development subset and evaluated once on held-out subjects.

## Reproduction

Run:

```bash
python experiments/bidmc_llm_capture/hysteresis_ablation.py
```

The exact table is written to
`generated/hysteresis_subject_05.csv`. The script also asserts that equal
entry and exit thresholds reproduce the original subject 1 construction.
