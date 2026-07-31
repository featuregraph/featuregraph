import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from scripts.reproduce import (
    load_manifest,
    validate_expected_outputs,
    validate_object_tables,
)


def object_tables() -> tuple[SimpleNamespace, SimpleNamespace]:
    oscillations = pd.DataFrame(
        {
            "subject": [1],
            "oscillation_id": [1],
            "is_complete": [True],
            "start_index": [0],
            "peak_index": [2],
            "end_index": [5],
            "rise_duration": [2],
            "fall_duration": [3],
            "duration": [5],
        }
    )
    accumulations = pd.DataFrame(
        {
            "subject": [1],
            "accumulation_id": [1],
            "is_complete": [True],
        }
    )
    return (
        SimpleNamespace(table=oscillations, group=("subject",)),
        SimpleNamespace(table=accumulations),
    )


def test_validate_object_tables_accepts_matching_complete_objects() -> None:
    oscillation, accumulation = object_tables()

    validate_object_tables(
        "example",
        oscillation,
        accumulation,
    )


def test_validate_object_tables_rejects_mismatched_parent_ids() -> None:
    oscillation, accumulation = object_tables()
    accumulation.table.loc[0, "accumulation_id"] = 2

    with pytest.raises(RuntimeError, match="object IDs differ"):
        validate_object_tables(
            "example",
            oscillation,
            accumulation,
        )


def test_validate_object_tables_rejects_invalid_boundaries() -> None:
    oscillation, accumulation = object_tables()
    oscillation.table.loc[0, "peak_index"] = 0

    with pytest.raises(RuntimeError, match="boundary order"):
        validate_object_tables(
            "example",
            oscillation,
            accumulation,
        )


def test_load_manifest_reads_versioned_inputs(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "seed": 1729,
                "datasets": {"example": {"revision": "abc123"}},
                "outputs": ["table.csv"],
            }
        ),
        encoding="utf-8",
    )

    manifest = load_manifest(path)

    assert manifest["seed"] == 1729
    assert manifest["datasets"]["example"]["revision"] == "abc123"


def test_load_manifest_rejects_unsupported_schema(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "seed": 1729,
                "datasets": {},
                "outputs": ["table.csv"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported"):
        load_manifest(path)


def test_validate_expected_outputs_requires_manifest_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "present.csv").write_text("value\n1\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="missing.csv"):
        validate_expected_outputs(
            tmp_path,
            ["present.csv", "missing.csv"],
        )
