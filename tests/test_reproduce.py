from types import SimpleNamespace

import pandas as pd
import pytest

from scripts.reproduce import validate_object_tables


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
