import pandas as pd

from scripts.run_physionet_nori_demonstration import (
    PHYSIOLOGY_COLUMNS,
    PROTOCOL_STATES,
    feature_matrix,
    validate_fold_assignments,
)


def _objects() -> pd.DataFrame:
    rows = []
    for index, state in enumerate(PROTOCOL_STATES):
        row = {
            "subject_id": f"subject_{index}",
            "cohort": "v1" if index % 2 == 0 else "v2",
            "protocol_state": state,
            "self_reported_stress": float(index),
        }
        row.update(
            {
                column: float(index + offset)
                for offset, column in enumerate(PHYSIOLOGY_COLUMNS)
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def test_feature_conditions_exclude_target_and_participant() -> None:
    objects = _objects()
    physiology = feature_matrix(objects, "physiology_only")
    with_protocol = feature_matrix(objects, "physiology_plus_protocol")

    assert list(physiology.columns) == list(PHYSIOLOGY_COLUMNS)
    assert "subject_id" not in with_protocol
    assert "self_reported_stress" not in with_protocol
    assert len(with_protocol.columns) == len(PHYSIOLOGY_COLUMNS) + len(PROTOCOL_STATES)
    assert with_protocol.filter(like="protocol_").sum().eq(1).all()


def test_fold_validation_rejects_participant_overlap() -> None:
    assignments = pd.DataFrame(
        {
            "subject_id": [f"subject_{index}" for index in range(10)],
            "cohort": ["v1"] * 5 + ["v2"] * 5,
            "fold": [1, 2, 3, 4, 5] * 2,
        }
    )
    objects = assignments[["subject_id", "cohort"]].copy()
    validate_fold_assignments(objects, assignments)

    duplicated = pd.concat([assignments, assignments.iloc[[0]]], ignore_index=True)
    try:
        validate_fold_assignments(objects, duplicated)
    except AssertionError as error:
        assert "more than one fold" in str(error)
    else:
        raise AssertionError("Expected duplicate participant assignment to fail")
