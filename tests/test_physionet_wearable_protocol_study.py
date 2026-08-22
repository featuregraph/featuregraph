import pandas as pd

import featuregraph as fg
from scripts.run_physionet_wearable_protocol_study import (
    PROTOCOLS,
    STATE_CONTRACT,
    compiled_objects,
    declared_intervals,
    match_declared_to_compiled,
    protocol_timeline,
)


def _tags(count: int) -> pd.DatetimeIndex:
    return pd.date_range("2026-01-01", periods=count, freq="1min", tz="UTC")


def test_protocol_versions_have_stable_declared_schema() -> None:
    v1 = declared_intervals("S01", _tags(13))
    v2 = declared_intervals("f01", _tags(9))

    assert list(v1.columns) == list(v2.columns)
    assert v1["protocol_state"].tolist() == [row[0] for row in PROTOCOLS["v1"]]
    assert v2["protocol_state"].tolist() == [row[0] for row in PROTOCOLS["v2"]]


def test_external_boundaries_round_trip_through_compiler() -> None:
    tags = _tags(13)
    declared = declared_intervals("S01", tags)
    timeline = protocol_timeline("S01", tags, declared)
    compiled = fg.compile_states(timeline, STATE_CONTRACT).observations
    objects = compiled_objects(compiled)
    mapped = match_declared_to_compiled(declared, objects)

    assert mapped["boundary_exact"].all()
    assert "unassigned" in compiled["state"].unique()
    assert (
        compiled["enter_protocol_state"].sum()
        == compiled["exit_protocol_state"].sum()
    )


def test_protocol_rejects_missing_required_tags() -> None:
    try:
        declared_intervals("S01", _tags(5))
    except ValueError as error:
        assert "required" in str(error)
    else:
        raise AssertionError("Expected incomplete tags to be rejected")
