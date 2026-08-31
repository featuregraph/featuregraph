# BIDMC 85-sample respiratory-object study

## Approved change

The rolling-envelope window was changed from the registered 79- and 100-sample
variants to **85 samples**. The dataset, state contract, numerical
tolerance, trough–peak–trough boundaries, completeness rules, comparator,
matching tolerance, measurements, and claim limits were unchanged.

## Result

- Participants: 53
- Source observations evaluated: 3,180,053
- Complete 85-sample objects: 8,489
- Objects with period measurements: 8,437
- Mean period: 2.9518 seconds
- Median period: 3.0880 seconds
- Mean object rate: 23.7567 breaths/minute
- Median object rate: 19.4301 breaths/minute
- Comparator matches: 7,098
- 85-sample-only objects relative to the comparator: 1,391
- Comparator-only objects: 70
- All validation checks passed: True

## Interpretation

The mean period is the object-weighted average period of complete BIDMC
respiratory objects produced by this exact 85-sample construction. It is not a
universal estimate of human breathing and does not establish clinical breath
validity.

## Window comparison

| window_samples | effective_support_samples | complete_objects | period_measurements | mean_period_seconds | median_subject_period_seconds |
| --- | --- | --- | --- | --- | --- |
| 79 | 157 | 8780 | 8727 | 2.8529675719032883 | 3.196 |
| 85 | 169 | 8489 | 8437 | 2.951770534550196 | 3.224 |
| 100 | 199 | 7926 | 7873 | 3.172552267242475 | 3.288 |

## Reproduction

```bash
python -m scripts.run_bidmc_parameterized_window_study --window 85
```

The exact declarative contract and its SHA-256 fingerprint are stored in
`study_contract.json`; the public aggregate payload is stored in
`api_record.json`. The complete curated object table is published as
`complete_objects_part_001.csv`, `complete_objects_part_002.csv`, `complete_objects_part_003.csv`.
