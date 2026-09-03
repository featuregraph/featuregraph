# Contracts that carry their own derivation

Two published constructions build their signal in pandas before anything
reaches the compiler: the BIDMC respiratory envelope
(`notebooks/researcher_input/bidmc_researcher_input.ipynb`) and the TEP
reactor-pressure envelope (`notebooks/researcher_input/tep_researcher_input.ipynb`).
Both are a rolling maximum, a rolling mean, a backward shift, and a first
difference, and both partition that difference into rising, falling, and
inactive.

The contracts here express the same constructions entirely inside a
`state-contract-v2` contract, so the whole construction, preprocessing
included, is one fingerprinted document. Nothing outside the contract shapes
the states.

| Contract | Source records | Group column | Derived columns |
| --- | --- | --- | --- |
| `bidmc_respiration_states_v2.json` | BIDMC 1.0.0, 53 subjects, `respiration` at 125 Hz | `subject_id` | `respiration_smooth`, `respiration_change` |
| `tep_reactor_pressure_states_v2.json` | Tennessee Eastman Fault 2, simulation runs 1 to 10 | `simulation_run` | `reactor_pressure_smooth`, `reactor_pressure_change`, `time_step_hours`, `reactor_pressure_rate` |

These are not the frozen study contracts. The published studies keep their
own contracts and fingerprints under `artifacts/studies/`, unchanged. These
carry no approval record and execute nothing on their own.

## Verification

`scripts/verify_derived_contracts.py` runs each contract against the source
records alongside the published path, the preprocessing exactly as the
notebooks write it followed by the published state rules, and compares them
row by row: the valid mask, every derived column, every state mask, the
occurrence identifiers, and every event. One row per record goes to
`verification/<dataset>_equivalence.csv`, with the environment and contract
fingerprints in `verification/<dataset>_summary.json`.

The TEP exit event needs one note. The published TEP study, which predates the
compiler, places the exit-rising event on the first sample after a rising run.
The compiler's `exit_state` places it on the last rising sample. The
verification compares the compiler's exit shifted forward by one sample
against the published one; that is the same boundary under two conventions,
not a different construction.

```bash
python -m scripts.verify_derived_contracts --dataset tep
python -m scripts.verify_derived_contracts --dataset bidmc     # needs PhysioNet
```

`verification/tep_equivalence.csv` records 10 of 10 Fault 2 runs identical on
every check. Each run compiles to 3,001 observations, of which 99 are excluded:
49 leading, where two full 50-sample windows and the first difference are
undefined, and 50 trailing, where the backward shift is undefined. No interior
observation is excluded in any run.

`verification/bidmc_equivalence.csv` records 53 of 53 subjects identical on
every check: valid mask, both derived columns, all three state masks, the
occurrence identifiers, and both events. Each subject compiles to 60,001
observations, of which 199 are excluded: 99 leading, where two full
100-sample windows, the backward shift, and the first difference are
undefined, and 100 trailing, where the shift is undefined. No interior
observation is excluded in any subject. The run was made outside this
repository's continuous integration, because PhysioNet is not reachable from
it; `verification/bidmc_summary.json` records the environment and the
contract fingerprint.

Together the two tables say that the entire published BIDMC and TEP
constructions, preprocessing included, execute from a single contract each,
through a compiler that read none of it as science.
