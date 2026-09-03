"""Shape measures: they read compiled occurrences and know nothing else."""

import numpy as np
import pandas as pd
import pytest

from featuregraph import compile_states, shape


def _compiled(labels, *, group=None, version="state-contract-v1", policy="error"):
    frame = pd.DataFrame({"label": labels})
    contract = {"version": version, "state_column": "label", "missing_policy": policy}
    if group is not None:
        frame["record"] = group
        contract["group_by"] = "record"
    return compile_states(frame, contract).observations


def _sawtooth(rise: int, fall: int, cycles: int) -> list[str]:
    return (["rising"] * rise + ["falling"] * fall) * cycles


# -- occurrences ----------------------------------------------------------


def test_occurrences_agree_with_the_compiler_report():
    observations = _compiled(_sawtooth(3, 1, 4))

    table = shape.occurrences(observations)

    assert len(table) == 8
    assert table["sample_count"].tolist() == [3, 1] * 4
    assert table["start_position"].tolist() == [0, 3, 4, 7, 8, 11, 12, 15]
    assert table["end_position"].tolist() == [2, 3, 6, 7, 10, 11, 14, 15]


def test_occurrences_keep_record_positions_under_exclude():
    observations = _compiled(
        [None, None, "rising", "rising", None, "falling", "falling"],
        version="state-contract-v2",
        policy="exclude",
    )

    table = shape.occurrences(observations)

    # The rise starts at row 2 of the record, not at row 0 of the valid rows,
    # and the interior gap at row 4 is not counted as part of any run.
    assert table["start_position"].tolist() == [2, 5]
    assert table["end_position"].tolist() == [3, 6]
    assert table["sample_count"].tolist() == [2, 2]


def test_occurrences_refuse_uncompiled_frames():
    with pytest.raises(ValueError, match="compile_states"):
        shape.occurrences(pd.DataFrame({"x": [1]}))


# -- asymmetry ------------------------------------------------------------


@pytest.mark.parametrize(
    ("rise", "fall", "expected"), [(3, 1, 0.75), (2, 2, 0.5), (1, 3, 0.25)]
)
def test_asymmetry_is_the_rising_share_of_each_cycle(rise, fall, expected):
    observations = _compiled(_sawtooth(rise, fall, 3))

    result = shape.rise_fall_asymmetry(observations)

    assert result["paired"].all()
    assert result["asymmetry"].tolist() == [expected] * 3
    assert result["rising_occurrence_id"].tolist() == [0, 2, 4]
    assert result["falling_occurrence_id"].tolist() == [1, 3, 5]


def test_an_unpaired_rise_is_reported_not_dropped():
    observations = _compiled(
        ["rising", "rising", "inactive", "falling", "rising", "falling", "rising"]
    )

    result = shape.rise_fall_asymmetry(observations)

    assert result["paired"].tolist() == [False, True, False]
    assert result["asymmetry"].isna().tolist() == [True, False, True]
    assert result["falling_samples"].isna().tolist() == [True, False, True]
    assert result.loc[1, "asymmetry"] == 0.5


def test_asymmetry_does_not_pair_across_groups():
    labels = ["rising", "rising"] + ["falling", "falling"]
    observations = _compiled(labels, group=["a", "a", "b", "b"])

    result = shape.rise_fall_asymmetry(observations, group_by="record")

    assert result["record"].tolist() == ["a"]
    assert not result["paired"].iloc[0]


# -- drift ----------------------------------------------------------------


def test_drift_is_zero_when_durations_are_constant():
    observations = _compiled(_sawtooth(3, 1, 6))

    drift = shape.occurrence_drift(observations)

    by_state = drift.set_index("state")
    assert by_state.loc["rising", "occurrences"] == 6
    assert by_state.loc["rising", "slope"] == 0.0
    assert by_state.loc["rising", "first_half_median"] == 3.0
    assert by_state.loc["rising", "second_half_median"] == 3.0


def test_drift_slope_is_the_fitted_change_over_the_record():
    # Rises of 2, 4, 6, 8 samples, each followed by a one-sample fall.
    labels = []
    for rise in (2, 4, 6, 8):
        labels += ["rising"] * rise + ["falling"]
    observations = _compiled(labels)

    drift = shape.occurrence_drift(observations).set_index("state")

    assert drift.loc["rising", "slope"] > 0
    assert (
        drift.loc["rising", "first_half_median"]
        < drift.loc["rising", "second_half_median"]
    )
    assert drift.loc["falling", "slope"] == 0.0
    # A perfectly linear growth against normalised position reproduces the
    # span of the measure: from 2 samples at the start to 8 at the end.
    x = np.array([0, 3, 8, 15]) / (len(labels) - 1)
    y = np.array([2.0, 4.0, 6.0, 8.0])
    expected = np.polyfit(x, y, 1)[0]
    assert drift.loc["rising", "slope"] == pytest.approx(expected)


def test_drift_is_measured_within_each_group():
    growing = []
    for rise in (1, 2, 3):
        growing += ["rising"] * rise + ["falling"]
    shrinking = []
    for rise in (3, 2, 1):
        shrinking += ["rising"] * rise + ["falling"]
    observations = _compiled(
        growing + shrinking, group=["g"] * len(growing) + ["s"] * len(shrinking)
    )

    drift = shape.occurrence_drift(observations, group_by="record")
    rising = drift[drift["state"] == "rising"].set_index("record")

    assert rising.loc["g", "slope"] > 0
    assert rising.loc["s", "slope"] < 0
    # Each group is fitted on its own positions, normalised over its own length.
    growing_fit = np.polyfit(np.array([0, 2, 5]) / 8, [1.0, 2.0, 3.0], 1)[0]
    shrinking_fit = np.polyfit(np.array([0, 4, 7]) / 8, [3.0, 2.0, 1.0], 1)[0]
    assert rising.loc["g", "slope"] == pytest.approx(growing_fit)
    assert rising.loc["s", "slope"] == pytest.approx(shrinking_fit)


def test_drift_needs_two_occurrences_for_a_slope():
    observations = _compiled(["rising", "rising", "falling"])

    drift = shape.occurrence_drift(observations).set_index("state")

    assert np.isnan(drift.loc["rising", "slope"])
    assert drift.loc["rising", "occurrences"] == 1


def test_drift_refuses_an_unknown_measure():
    with pytest.raises(ValueError, match="Unknown occurrence measure"):
        shape.occurrence_drift(_compiled(_sawtooth(1, 1, 2)), measure="height")
