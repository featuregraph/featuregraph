"""Execute the generated BIDMC study from the frozen researcher input.

This file is implementation infrastructure. Scientific and representational
choices belong in notebooks/bidmc_researcher_input.ipynb.
"""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import pandas as pd
import scipy


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_NOTEBOOK = REPO_ROOT / "notebooks" / "bidmc_researcher_input.ipynb"
EXECUTION_NOTEBOOK = REPO_ROOT / "notebooks" / "transition_wave_study.ipynb"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "bidmc_researcher_workflow"


def notebook_sources(path: Path) -> list[str]:
    notebook = json.loads(path.read_text())
    return [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def researcher_values(source: str) -> dict[str, object]:
    """Evaluate only declarative top-level assignments from the input cell."""
    tree = ast.parse(source)
    values: dict[str, object] = {}
    safe_globals = {"__builtins__": {}, "list": list, "range": range}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            expression = ast.Expression(node.value)
            value = eval(compile(expression, str(INPUT_NOTEBOOK), "eval"), safe_globals, values)
        except Exception:
            continue
        values[target.id] = value
    return values


def validate_binding(input_source: str, execution_source: str, values: dict[str, object]) -> None:
    assert len(notebook_sources(INPUT_NOTEBOOK)) == 1
    compile(input_source, str(INPUT_NOTEBOOK), "exec")

    assert values["subject_ids"] == list(range(1, 54))
    assert values["sampling_rate_hz"] == 125
    assert values["smooth_window"] == 100
    assert values["numerical_atol"] == 1e-12
    assert values["expected_samples_per_subject"] == 60001
    assert values["matching"]["tolerance_samples"] == 63
    assert values["comparator"]["filter"] == "fourth-order Butterworth low-pass"
    assert values["comparator"]["cutoff_hz"] == 0.8
    assert values["comparator"]["minimum_distance_samples"] == 188
    assert values["comparator"]["minimum_prominence"] == 0.08

    required_execution_fragments = [
        'FS = 125',
        'W = 100',
        'TOL = 63',
        'NUMERICAL_ATOL = 1e-12',
        'EXPECTED_SIGNAL_ROWS = 60001',
        'butter(4, 0.8, btype="lowpass"',
        'find_peaks(filtered, distance=188, prominence=0.08)',
        'find_peaks(-filtered, distance=188, prominence=0.08)',
    ]
    missing = [fragment for fragment in required_execution_fragments if fragment not in execution_source]
    assert not missing, f"Execution notebook is not bound to the researcher input: {missing}"


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()


def execute_notebook_sources(sources: list[str]) -> tuple[dict[str, object], str]:
    namespace: dict[str, object] = {"__name__": "__main__"}
    output = io.StringIO()
    with redirect_stdout(output):
        for source in sources:
            exec(compile(source, str(EXECUTION_NOTEBOOK), "exec"), namespace)
    return namespace, output.getvalue()


def save_dataframe(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(OUTPUT_ROOT / f"{name}.csv.gz", index=False, compression="gzip")


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    input_sources = notebook_sources(INPUT_NOTEBOOK)
    execution_sources = notebook_sources(EXECUTION_NOTEBOOK)
    input_source = input_sources[0]
    execution_source = "\n\n".join(execution_sources)
    values = researcher_values(input_source)
    validate_binding(input_source, execution_source, values)

    namespace, console_output = execute_notebook_sources(execution_sources)
    (OUTPUT_ROOT / "console_output.txt").write_text(console_output)

    save_dataframe(namespace["subject_summary"], "subject_summary")
    save_dataframe(namespace["matched_objects"], "matched_objects")
    save_dataframe(namespace["featuregraph_only_objects"], "featuregraph_only_objects")
    save_dataframe(namespace["baseline_only_objects"], "comparator_only_objects")
    save_dataframe(namespace["invalidated_objects"], "invalidated_objects")
    save_dataframe(namespace["annotation_summary"], "annotation_summary")
    save_dataframe(namespace["cohort_summary"], "cohort_summary")
    save_dataframe(namespace["window_sensitivity"], "window_sensitivity")

    all_featuregraph_objects = []
    all_comparator_objects = []
    observation_directory = OUTPUT_ROOT / "observations"
    observation_directory.mkdir(exist_ok=True)
    for subject in values["subject_ids"]:
        observations, objects, _, _ = namespace["construct"](subject)
        comparator_objects, _ = namespace["baseline"](subject)
        objects = objects.copy()
        comparator_objects = comparator_objects.copy()
        comparator_objects["subject_id"] = subject
        all_featuregraph_objects.append(objects)
        all_comparator_objects.append(comparator_objects)
        observations.to_csv(
            observation_directory / f"subject_{subject:02d}.csv.gz",
            index=False,
            compression="gzip",
        )

    save_dataframe(pd.concat(all_featuregraph_objects, ignore_index=True), "featuregraph_objects")
    save_dataframe(pd.concat(all_comparator_objects, ignore_index=True), "comparator_objects")

    cohort = namespace["cohort_summary"].iloc[0]
    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repository_commit": git_commit(),
        "researcher_input_path": str(INPUT_NOTEBOOK.relative_to(REPO_ROOT)),
        "researcher_input_sha256": file_sha256(INPUT_NOTEBOOK),
        "execution_notebook_path": str(EXECUTION_NOTEBOOK.relative_to(REPO_ROOT)),
        "execution_notebook_sha256": file_sha256(EXECUTION_NOTEBOOK),
        "python": sys.version,
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "subjects": int(cohort["subjects"]),
        "failures": int(cohort["failures"]),
        "featuregraph_complete_objects": int(cohort["featuregraph_complete_objects"]),
        "matched_objects": int(cohort["matched_objects"]),
        "featuregraph_only_objects": int(cohort["featuregraph_only_objects"]),
        "comparator_only_objects": int(cohort["baseline_only_objects"]),
    }
    (OUTPUT_ROOT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    validation_report = f"""# BIDMC generated-workflow validation

- Researcher input SHA-256: `{provenance['researcher_input_sha256']}`
- Execution notebook SHA-256: `{provenance['execution_notebook_sha256']}`
- Repository commit: `{provenance['repository_commit']}`
- Subjects: {provenance['subjects']}
- Execution failures: {provenance['failures']}
- Complete FeatureGraph objects: {provenance['featuregraph_complete_objects']}
- Matched objects: {provenance['matched_objects']}
- FeatureGraph-only objects: {provenance['featuregraph_only_objects']}
- Comparator-only objects: {provenance['comparator_only_objects']}

The researcher input contained exactly one code cell. Its declared parameters were
bound to the generated execution notebook before execution. All frozen notebook
regression assertions passed. Every signal download contained 60,001 rows, the RESP
column, and no missing RESP values. Object-level tables and per-subject observation,
state, and event tables are stored beside this report.
"""
    (OUTPUT_ROOT / "validation_report.md").write_text(validation_report)
    print(validation_report)


if __name__ == "__main__":
    main()
