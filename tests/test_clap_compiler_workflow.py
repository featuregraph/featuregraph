from pathlib import Path

from featuregraph.contracts.study_workflow import declarative_values, notebook_sources

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_NOTEBOOK = (
    REPO_ROOT / "notebooks" / "researcher_input" / "clap_researcher_input.ipynb"
)
EXECUTION_NOTEBOOK = (
    REPO_ROOT / "notebooks" / "generated_study" / "clap_generated_study.ipynb"
)


def test_generated_clap_default_matches_researcher_contract() -> None:
    researcher_source = "\n\n".join(notebook_sources(INPUT_NOTEBOOK))
    execution_source = notebook_sources(EXECUTION_NOTEBOOK)[0]
    researcher = declarative_values(researcher_source, INPUT_NOTEBOOK)
    generated = declarative_values(execution_source, EXECUTION_NOTEBOOK)

    assert researcher["state_contract"] == generated["DEFAULT_CLAP_STATE_CONTRACT"]
    assert 'state_contract=CLAP_STATE_CONTRACT' in "\n\n".join(
        notebook_sources(EXECUTION_NOTEBOOK)
    )
