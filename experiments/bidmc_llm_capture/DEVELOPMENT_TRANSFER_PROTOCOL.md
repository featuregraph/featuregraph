# Development-versus-transfer protocol

This protocol fixes the evidential status of every BIDMC experiment. It exists
to prevent development agreement, post hoc diagnostics, and independent
transfer from being combined under one label.

## Completed study phases

| Phase | Records | Rule status | Allowed actions | Claims supported |
| --- | --- | --- | --- | --- |
| Exploratory development | Subject 1 | Mutable | Inspect signal; choose parameters; debug boundaries; harmonize measurement contracts | Feasibility and development-record agreement |
| Frozen absolute transfer | Subjects 2–53 | LLM/SciPy and FeatureGraph absolute rules locked after subject 1 | Execute unchanged; compare objects and annotations; no subject-specific tuning or manual correction | Transfer performance of the original frozen representation |
| Post-transfer MAD diagnosis | Subjects 1–53; paired aggregate restricted to 51 records with nonzero MAD | One threshold calibrated from subject 1; normalization proposed after absolute results were known | Run shared rule; report zero-scale failures; compare paired outcomes | Mechanistic ablation, not independent validation |
| Subject 5 hysteresis diagnosis | Subject 5 | Exploratory variants | Inspect one failure and vary exit threshold | Local diagnostic only |

## Freeze boundary for the absolute transfer pass

Before subjects 2–53 were evaluated, the following were fixed:

- the context-isolated LLM/SciPy detector and endpoint rules;
- FeatureGraph `diff_lag=45`, `eps=0.15`, `max_state_gap=7`, and no smoothing;
- complete-object and endpoint definitions;
- period, full-excursion, radius-amplitude, and symmetry contracts;
- ordered one-to-one matching within 63 samples; and
- the rule that annotations are evaluated only after construction.

No transfer subject received a tuned threshold, edited boundary, or fallback
selected from its outcome.

## Interpretation rules

1. Subject 1 statistics are development results, not generalization evidence.
2. Agreement with the frozen LLM/SciPy path is detector agreement, not clinical
   accuracy.
3. Annotation agreement is external diagnostic evidence, not a clinical
   sensitivity or positive-predictive-value estimate.
4. MAD normalization is post hoc because absolute-transfer outcomes motivated
   it, even though its threshold was calibrated only on subject 1.
5. Subjects 35 and 39 are mathematical failures of MAD scaling and remain
   visible; they are not zero-count successes and are not silently discarded.
6. Hysteresis on subject 5 cannot support a cohort-level claim.

## Required protocol for the transition-only successor study

Before final test outcomes are inspected:

1. declare the dataset and record-level development, validation, and untouched
   test split, or name an external test dataset;
2. define transition states, gap handling, boundary events, completeness, and
   object relations without semantic oscillation assumptions;
3. register the full parameter search space and selection criterion;
4. archive every attempted development/validation configuration;
5. freeze code, environment, measurement contracts, matching rules, and the
   object schema;
6. publish or timestamp the locked contract; and
7. execute one final test pass without subject-specific corrections.

Any modification after examining test results begins a new development cycle
and requires new untouched data for a confirmatory transfer claim.
