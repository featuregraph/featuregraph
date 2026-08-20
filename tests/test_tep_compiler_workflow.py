from pathlib import Path

import numpy as np
import pandas as pd

from featuregraph.contracts.study_workflow import (
    declarative_values,
    execute_notebook_sources,
    notebook_sources,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_NOTEBOOK = (
    REPO_ROOT / "notebooks" / "researcher_input" / "tep_researcher_input.ipynb"
)
EXECUTION_NOTEBOOK = (
    REPO_ROOT / "notebooks" / "generated_study" / "tep_generated_study.ipynb"
)


def _contract() -> dict[str, object]:
    source = notebook_sources(INPUT_NOTEBOOK)[0]
    return declarative_values(source, INPUT_NOTEBOOK)["state_contract"]


def test_generated_tep_default_matches_researcher_contract() -> None:
    source = notebook_sources(EXECUTION_NOTEBOOK)[0]
    generated = declarative_values(source, EXECUTION_NOTEBOOK)

    assert generated["DEFAULT_TEP_STATE_CONTRACT"] == _contract()


def test_tep_compiler_projection_preserves_legacy_events() -> None:
    sources = notebook_sources(EXECUTION_NOTEBOOK)
    namespace, _ = execute_notebook_sources(
        sources[:1],
        EXECUTION_NOTEBOOK,
        initial_namespace={"TEP_STATE_CONTRACT": _contract()},
    )
    sample_index = np.arange(180)
    source = pd.DataFrame(
        {
            "time_(h)": sample_index / 60,
            "reactor_pressure": 2800 + np.sin(sample_index / 7),
            "fault_number": 2,
            "simulation_run": 999,
        }
    )

    observations, _, provenance = namespace["construct_observations"](source)

    valid = observations["reactor_pressure_valid"]
    assert observations.loc[valid, "reactor_pressure_state"].notna().all()
    assert observations.loc[valid, "reactor_pressure_state_occurrence_id"].notna().all()
    assert observations["reactor_pressure_peak"].equals(
        observations["exit_reactor_pressure_rising"]
    )
    assert provenance["state_contract_version"] == "state-contract-v1"
