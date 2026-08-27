# Nori downstream interoperability on PhysioNet protocol objects

## Question

Can an independent tabular foundation model operate directly on explicit
FeatureGraph protocol occurrences, and can that integration be evaluated
without losing participant boundaries, declared experimental states, or the
distinction between representation and prediction?

This exploratory demonstration uses Nori V1 to estimate the source
self-reported stress value associated with each preserved protocol occurrence.
It is a downstream interoperability test, not a stress detector or a
reproduction of Synthefy's benchmark suite.

## Upstream representation

The input is produced unchanged by the completed [PhysioNet wearable protocol
representation study](physionet_wearable_protocol_study.md):

- 33 eligible participants;
- 248 exactly bounded baseline, task, and rest occurrences;
- 248 source self-reports joined one-to-one;
- native-rate heart-rate, electrodermal-activity, and skin-temperature
  measurements summarized within every occurrence;
- participant, protocol, boundary, and provenance fields retained separately
  from model predictors.

FeatureGraph determines what each row represents and which observations support
it. Nori, XGBoost, and LightGBM receive the resulting numeric table and remain
responsible only for prediction.

## Frozen predictive contract

The contract and estimator configurations were written before model execution.

| Decision | Frozen value |
| --- | --- |
| Target | Source `self_reported_stress`, range 0–10 |
| Unit of prediction | One declared protocol occurrence |
| Evaluation | Five participant-held-out folds |
| Fold stratification | Protocol version crossed with low/high participant mean target |
| Participants | 33; each appears in exactly one test fold |
| Predictors excluded | Participant ID, cohort ID, timestamps, object ID, and target |
| Primary metric | Pooled out-of-fold mean absolute error (MAE) |
| Secondary metrics | Root mean squared error and pooled out-of-fold R² |

The same folds and rows are used for every model. Stratification uses the
participant-level target only to balance fold assignment; it is never supplied
as a predictor. Every fold contains both published protocol versions.

Two feature conditions test whether the declared protocol itself changes the
result:

1. **Physiology only:** mean, median, minimum, and maximum for heart rate, EDA,
   and temperature (12 columns).
2. **Physiology plus protocol:** the same 12 measurements plus a fixed one-hot
   encoding of the declared protocol state.

The models are a fold-specific training mean, Nori 6M, XGBoost, and LightGBM.
Nori uses the public `nori-6m` checkpoint through `synthefy-nori==0.20.0` on
CPU. Strict pipeline mode rejects a degraded Nori execution rather than scoring
it silently. XGBoost and LightGBM use the fixed configurations in the study
contract; they were not tuned, so this is not evidence about tuned benchmark
performance.

## Results

All 1,984 expected out-of-fold predictions were produced: 248 occurrences ×
two feature conditions × four models.

| Condition | Model | MAE | RMSE | R² |
| --- | --- | ---: | ---: | ---: |
| Physiology only | Training mean | **1.6853** | **2.0725** | **−0.0149** |
| Physiology only | Nori 6M | 1.8217 | 2.2826 | −0.2310 |
| Physiology only | XGBoost | 1.8684 | 2.3740 | −0.3316 |
| Physiology only | LightGBM | 1.9173 | 2.4122 | −0.3748 |
| Physiology + protocol | Training mean | **1.6853** | **2.0725** | **−0.0149** |
| Physiology + protocol | Nori 6M | 1.7739 | 2.1795 | −0.1224 |
| Physiology + protocol | XGBoost | 1.7916 | 2.2412 | −0.1868 |
| Physiology + protocol | LightGBM | 1.8246 | 2.2758 | −0.2238 |

The training-mean control had the lowest pooled MAE in both conditions. Every
learned model had negative pooled out-of-fold R². Therefore, this demonstration
does **not** establish that these interval summaries predict self-reported
stress for unseen participants.

Nori nevertheless ranked first among the three learned models in both feature
conditions. With physiology plus protocol, its MAE was 1.7739, compared with
1.7916 for XGBoost and 1.8246 for LightGBM. Adding the declared protocol state
reduced Nori's MAE by 2.6%, XGBoost's by 4.1%, and LightGBM's by 4.8%.

The participant-level comparison is heterogeneous. In the physiology-plus-
protocol condition, Nori had lower participant MAE than the training mean for
19 of 33 participants, lower MAE than XGBoost for 15 of 33, and lower MAE than
LightGBM for 20 of 33. Its pooled advantage over the other learned models is
therefore an error-magnitude result, not a universal participant-level win.

## What the demonstration establishes

The completed run establishes a concrete software boundary:

```text
PhysioNet observations and tags
    → FeatureGraph protocol occurrences and measurements
    → frozen participant-held-out table
    → Nori / XGBoost / LightGBM
    → inspectable out-of-fold predictions
```

- Nori consumed the FeatureGraph object table without a task-specific training
  loop or a study-specific adapter.
- Participant identity remained available for evaluation while being excluded
  from model inputs.
- Protocol state could be added as an explicit, inspectable condition rather
  than being hidden in preprocessing.
- The negative control prevented a learned-model ranking from being mistaken
  for evidence of useful out-of-participant prediction.
- Every model output can be traced to a participant, protocol occurrence, fold,
  feature condition, package version, and frozen contract.

This is the intended complementarity: FeatureGraph constructs and preserves the
scientific rows; a downstream model predicts from them.

## Claim boundary

This study does not show that:

- wearable measurements identify psychological stress;
- protocol tasks caused the recorded physiological changes;
- Nori, XGBoost, or LightGBM generalizes adequately to unseen participants;
- Nori beats tuned gradient-boosting models or reproduces Synthefy's published
  benchmark results;
- explicit FeatureGraph construction improves predictive accuracy over every
  alternative representation.

The result is an executed interoperability demonstration with an informative
negative predictive result. A larger confirmatory study would need a
prospectively frozen target, representation comparison, estimator-tuning
policy, and external participant cohort.

## Reproduction and frozen evidence

From the repository root:

```bash
python -m pip install -e ".[nori-study]"
python scripts/run_physionet_nori_demonstration.py
```

The runner downloads the public PhysioNet sources, reconstructs and validates
the 248 upstream objects, creates the participant-held-out folds, downloads the
open Nori weights once, executes every model-condition pair, and writes the
complete evidence table.

- [Executable demonstration](../../scripts/run_physionet_nori_demonstration.py)
- [Study contract and exact package versions](physionet_nori/study_contract.json)
- [Fold assignments](physionet_nori/fold_assignments.csv)
- [Complete out-of-fold predictions](physionet_nori/predictions.csv)
- [Fold metrics](physionet_nori/fold_metrics.csv)
- [Pooled summary](physionet_nori/summary.csv)
- [Participant metrics](physionet_nori/subject_metrics.csv)
- [Paired participant comparisons](physionet_nori/paired_comparisons.csv)
- [Focused tests](../../tests/test_physionet_nori_demonstration.py)
