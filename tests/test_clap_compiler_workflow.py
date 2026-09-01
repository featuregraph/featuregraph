from pathlib import Path

import pandas as pd

import featuregraph as fg
from featuregraph.studies import notebook_sources, researcher_values

INPUT_NOTEBOOK = Path("notebooks/researcher_input/clap_researcher_input.ipynb")
GENERATED_NOTEBOOK = Path("notebooks/generated_study/clap_generated_study.ipynb")


def _researcher_contract() -> dict[str, object]:
    source = notebook_sources(INPUT_NOTEBOOK)[0]
    return researcher_values(source)["clap_state_contract"]


def test_generated_clap_contract_matches_researcher_input() -> None:
    generated_source = "\n\n".join(notebook_sources(GENERATED_NOTEBOOK))
    generated_contract = researcher_values(generated_source)["CLAP_STATE_CONTRACT"]

    assert generated_contract == _researcher_contract()
    assert generated_contract["version"] == "state-contract-v1"
    assert "fg.compile_states(" in generated_source


def test_external_state_compiler_matches_object_adapter_boundaries() -> None:
    states = [1, 1, 2, 2, 1]
    compiled = fg.compile_states(
        pd.DataFrame({"clap_state": states}), _researcher_contract()
    ).observations
    objects = fg.from_state_sequence(states).observations

    assert compiled["state"].tolist() == states
    assert compiled["state_occurrence_id"].tolist() == objects[
        "occurrence_id"
    ].tolist()
    assert compiled["enter_state_occurrence"].tolist() == objects[
        "enter_state_occurrence"
    ].tolist()
    assert compiled["exit_state_occurrence"].tolist() == objects[
        "exit_state_occurrence"
    ].tolist()
