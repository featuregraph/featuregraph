import numpy as np
import pytest

import featuregraph as fg
from featuregraph.behaviors.feature_object import ObjectStatus
from featuregraph.operators.events import enter_label, exit_label


def test_recurring_labels_become_distinct_occurrence_objects():
    result = fg.from_state_sequence(
        [1, 1, 2, 2, 2, 1],
        signal=[10, 11, 20, 21, 22, 12],
        group_id="example",
        dataset="test",
        signal_name="value",
        detector="fixture",
        software_version=fg.__version__,
    )

    assert len(result.objects) == 3
    assert [obj.measurement("state_label").value for obj in result.objects] == [1, 2, 1]
    assert [obj.measurement("sample_count").value for obj in result.objects] == [
        2,
        3,
        1,
    ]
    assert [obj.status for obj in result.objects] == [
        ObjectStatus.BOUNDARY_TRUNCATED,
        ObjectStatus.COMPLETE,
        ObjectStatus.BOUNDARY_TRUNCATED,
    ]
    assert np.array_equal(result.reconstruct_states(), [1, 1, 2, 2, 2, 1])
    assert result.relations[["source_state", "target_state"]].values.tolist() == [
        [1, 2],
        [2, 1],
    ]


def test_half_open_boundaries_cover_irregular_time_sequence():
    result = fg.from_state_sequence(
        ["a", "a", "b"], times=[0.0, 0.5, 1.5], time_unit="seconds"
    )

    assert result.objects[0].start.index == 0
    assert result.objects[0].end.index == 2
    assert result.objects[0].duration == 1.5
    assert result.objects[1].end.index == 3
    assert result.objects[1].end.time == 2.5


@pytest.mark.parametrize("states", [[], [1, np.nan]])
def test_invalid_state_sequences_are_rejected(states):
    with pytest.raises(ValueError):
        fg.from_state_sequence(states)


def test_aligned_inputs_are_required():
    with pytest.raises(ValueError):
        fg.from_state_sequence([1, 2], signal=[1.0])
    with pytest.raises(ValueError):
        fg.from_state_sequence([1, 2], times=[0.0])


def test_label_events_do_not_cross_group_boundaries():
    import pandas as pd

    labels = pd.Series(["a", "b", "b", "b", "a"])
    groups = pd.Series([1, 1, 2, 2, 2])

    assert enter_label(labels, groups).tolist() == [True, True, True, False, True]
    assert exit_label(labels, groups).tolist() == [True, True, False, True, True]
    assert enter_label(labels, groups, include_first=False).tolist() == [
        False,
        True,
        False,
        False,
        True,
    ]
    assert exit_label(labels, groups, include_last=False).tolist() == [
        True,
        False,
        False,
        True,
        False,
    ]
