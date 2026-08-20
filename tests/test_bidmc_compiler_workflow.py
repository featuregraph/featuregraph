import json
from pathlib import Path

import numpy as np
import pandas as pd

from featuregraph import compile_states
from scripts.run_bidmc_researcher_workflow import (
    EXECUTION_NOTEBOOK,
    INPUT_NOTEBOOK,
    canonical_json,
    notebook_sources,
    researcher_values,
    value_sha256,
)


def _workflow_contract() -> dict[str, object]:
    input_source = notebook_sources(INPUT_NOTEBOOK)[0]
    return researcher_values(input_source)["state_contract"]


def test_generated_notebook_default_matches_researcher_state_contract() -> None:
    execution_source = "\n\n".join(notebook_sources(EXECUTION_NOTEBOOK))
    generated_default = researcher_values(execution_source)[
        "DEFAULT_BIDMC_STATE_CONTRACT"
    ]

    assert _workflow_contract() == generated_default
    assert generated_default["version"] == "state-contract-v1"
    assert "fg.compile_states(" in execution_source


def test_contract_fingerprint_is_canonical() -> None:
    contract = _workflow_contract()
    reordered = json.loads(canonical_json(contract))

    assert value_sha256(contract) == value_sha256(reordered)
    assert len(value_sha256(contract)) == 64


def test_compiled_bidmc_states_and_boundaries_match_frozen_formulas() -> None:
    # The first sample represents the invalid envelope edge. The final run is
    # deliberately rising so the contract must not manufacture a terminal exit.
    prepared = pd.DataFrame(
        {
            "subject_id": 1,
            "sample_index": range(8),
            "respiration_change": [np.nan, 0.2, 0.3, 0.0, -0.2, 0.0, 0.2, 0.3],
        }
    )
    valid = prepared["respiration_change"].notna()
    compiled = compile_states(prepared.loc[valid], _workflow_contract()).observations

    legacy_rising = valid & prepared["respiration_change"].gt(1e-12)
    legacy_falling = valid & prepared["respiration_change"].lt(-1e-12)
    legacy_inactive = valid & prepared["respiration_change"].abs().le(1e-12)
    legacy_enter = valid & legacy_rising.astype(int).diff().eq(1)
    legacy_exit_at_peak = (valid & legacy_rising.astype(int).diff().eq(-1)).shift(
        -1, fill_value=False
    )

    assert compiled["state__rising"].equals(legacy_rising.loc[valid])
    assert compiled["state__falling"].equals(legacy_falling.loc[valid])
    assert compiled["state__inactive"].equals(legacy_inactive.loc[valid])
    assert compiled["enter_respiration_rising"].equals(legacy_enter.loc[valid])
    assert compiled["exit_respiration_rising"].equals(legacy_exit_at_peak.loc[valid])
    assert compiled.index[compiled["exit_respiration_rising"]].tolist() == [2]


def test_frozen_cohort_regression_guard_remains_in_generated_notebook() -> None:
    notebook = json.loads(Path(EXECUTION_NOTEBOOK).read_text())
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])

    expected_fragments = {
        '"featuregraph_complete_objects": 7926',
        '"matched_objects": 7086',
        '"featuregraph_only_objects": 840',
        '"baseline_only_objects": 82',
        "assert observed == expected",
    }
    assert all(fragment in source for fragment in expected_fragments)
