# FeatureGraph tutorials for pandas users

This directory is a beginner path from pandas observation tables to explicit
states, events, bounded occurrences, measurements, relations, and validation.
Fixtures are deterministic and network-free. They resemble BIDMC, PhysioNet
wearable, and Tennessee Eastman Process study structures, but are not source
data and do not reproduce the maintained results.

| Notebook | Topic |
| --- | --- |
| `00_from_pandas_to_featuregraph.ipynb` | Rows to occurrence objects |
| `01_bidmc_respiratory_states.ipynb` | Respiratory directional states |
| `02_bidmc_state_occurrence_objects.ipynb` | Boundaries, status, and relations |
| `03_physionet_protocol_occurrences.ipynb` | Protocol labels and wearable measurements |
| `04_tep_reactor_pressure_transitions.ipynb` | Frozen transfer across control runs |
| `05_cross_domain_same_contract.ipynb` | One contract across domains |

## Setup

```bash
python -m pip install -e ".[dev,notebooks]"
jupyter lab
```

Run in numerical order. These tutorials demonstrate deterministic structural
and analytical representation, not clinical detection, biomarker validity,
fault diagnosis, causal explanation, or prediction.

Full studies: [BIDMC](../../artifacts/studies/bidmc_object_workflow_study.md),
[PhysioNet](../../artifacts/studies/physionet_wearable_protocol_study.md), and
[TEP](../../artifacts/studies/tep_pressure_transfer_study.md).
