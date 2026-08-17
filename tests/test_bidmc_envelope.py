import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_series_equal

from experiments.bidmc_llm_capture.native_envelope import (
    ENVELOPE_SIGNAL,
    add_respiration_envelope,
    center_plateau_boundaries,
    centered_plateau_events,
    native_envelope_objects,
)


def test_envelope_matches_max_mean_shift_contract() -> None:
    observations = pd.DataFrame(
        {
            "subject": [1] * 7,
            "respiration": [1.0, 3.0, 2.0, 4.0, 0.0, 5.0, 1.0],
        }
    )

    result = add_respiration_envelope(observations, window=2, shift=2)

    assert_series_equal(
        result[ENVELOPE_SIGNAL],
        pd.Series(
            [3.0, 3.5, 4.0, 4.5, 5.0, np.nan, np.nan],
            name=ENVELOPE_SIGNAL,
        ),
    )
    assert_series_equal(
        result["respiration_raw"],
        observations["respiration"].rename("respiration_raw"),
    )


def test_envelope_does_not_cross_subject_boundaries() -> None:
    observations = pd.DataFrame(
        {
            "subject": [1, 1, 1, 1, 2, 2, 2, 2],
            "respiration": [1.0, 3.0, 2.0, 4.0, 10.0, 30.0, 20.0, 40.0],
        }
    )

    result = add_respiration_envelope(observations, window=2, shift=2)

    assert result.loc[result["subject"] == 1, ENVELOPE_SIGNAL].tolist()[:2] == [
        3.0,
        3.5,
    ]
    assert result.loc[result["subject"] == 2, ENVELOPE_SIGNAL].tolist()[:2] == [
        30.0,
        35.0,
    ]


@pytest.mark.parametrize("window", [0, -1])
def test_envelope_rejects_invalid_window(window: int) -> None:
    observations = pd.DataFrame(
        {"subject": [1], "respiration": [1.0]}
    )

    with pytest.raises(ValueError, match="at least 1"):
        add_respiration_envelope(observations, window=window)


def test_plateau_boundaries_use_floor_midpoints() -> None:
    features = pd.DataFrame(
        {
            "subject": [1] * 15,
            ENVELOPE_SIGNAL: (
                [0.0] * 3
                + [1.0] * 3
                + [0.0] * 3
                + [1.0] * 3
                + [0.0] * 3
            ),
        }
    )
    objects = pd.DataFrame(
        {
            "subject": [1, 1],
            "start_index": [2, 8],
            "peak_index": [3, 9],
            "end_index": [8, 14],
            "period": [np.nan, 6.0],
            "temporal_symmetry": [0.0, 0.0],
            "is_complete": [True, True],
        }
    )

    result = center_plateau_boundaries(objects, features)

    assert result["start_index"].tolist() == [1, 7]
    assert result["peak_index"].tolist() == [4, 10]
    assert result["end_index"].tolist() == [7, 13]
    assert result["peak_start_index"].tolist() == [3, 9]
    assert result["peak_end_index"].tolist() == [5, 11]
    assert result["peak_transition_index"].tolist() == [3, 9]
    assert result["peak_detection_index"].tolist() == [105, 111]
    assert result["peak_detection_latency_samples"].tolist() == [101, 101]
    assert not result["plateau_boundary_ambiguous"].any()
    assert not result["plateau_invalidated_complete"].any()
    assert result["transition_complete"].all()
    assert result["is_complete"].all()
    assert result["period"].iloc[1] == 6
    assert result["temporal_symmetry"].tolist() == [1.0, 1.0]


def test_even_plateau_uses_floor_midpoint() -> None:
    features = pd.DataFrame(
        {
            "subject": [1] * 10,
            ENVELOPE_SIGNAL: [0.0] * 3 + [1.0] * 4 + [0.0] * 3,
        }
    )
    objects = pd.DataFrame(
        {
            "subject": [1],
            "start_index": [2],
            "peak_index": [3],
            "end_index": [9],
            "period": [np.nan],
            "temporal_symmetry": [0.0],
            "is_complete": [True],
        }
    )

    result = center_plateau_boundaries(objects, features)

    assert result.at[0, "peak_start_index"] == 3
    assert result.at[0, "peak_end_index"] == 6
    assert result.at[0, "peak_index"] == 4


def test_rounded_extremum_remains_single_sample_interval() -> None:
    features = pd.DataFrame(
        {
            "subject": [1] * 5,
            ENVELOPE_SIGNAL: [0.0, 0.0, 1.0, 0.0, 0.0],
        }
    )
    objects = pd.DataFrame(
        {
            "subject": [1],
            "start_index": [1],
            "peak_index": [2],
            "end_index": [4],
            "period": [np.nan],
            "temporal_symmetry": [0.0],
            "is_complete": [True],
        }
    )

    result = center_plateau_boundaries(objects, features)

    assert result.at[0, "peak_start_index"] == 2
    assert result.at[0, "peak_end_index"] == 2
    assert result.at[0, "peak_index"] == 2
    assert result.at[0, "peak_detection_index"] == 102


def test_overlapping_extremum_intervals_are_flagged() -> None:
    features = pd.DataFrame(
        {
            "subject": [1] * 4,
            ENVELOPE_SIGNAL: [0.0, 1.0, 1.0, 0.0],
        }
    )
    objects = pd.DataFrame(
        {
            "subject": [1],
            "start_index": [0],
            "peak_index": [1],
            "end_index": [2],
            "period": [np.nan],
            "temporal_symmetry": [0.0],
            "is_complete": [True],
        }
    )

    result = center_plateau_boundaries(objects, features)

    assert result.at[0, "transition_complete"]
    assert result.at[0, "plateau_boundary_ambiguous"]
    assert result.at[0, "plateau_invalidated_complete"]
    assert not result.at[0, "is_complete"]


def test_plateau_event_centering_preserves_event_count() -> None:
    features = pd.DataFrame(
        {
            "subject": [1] * 9,
            ENVELOPE_SIGNAL: [0.0] * 3 + [1.0] * 3 + [0.0] * 3,
            f"{ENVELOPE_SIGNAL}_peak": [
                False,
                False,
                False,
                True,
                False,
                False,
                False,
                False,
                False,
            ],
        }
    )

    centered = centered_plateau_events(
        features,
        f"{ENVELOPE_SIGNAL}_peak",
    )

    assert centered == [4]


def test_plateau_event_centering_does_not_cross_groups() -> None:
    features = pd.DataFrame(
        {
            "subject": [1] * 6 + [2] * 6,
            ENVELOPE_SIGNAL: (
                [0.0, 0.0, 1.0, 1.0, 1.0, 0.0]
                + [1.0, 1.0, 1.0, 0.0, 0.0, 0.0]
            ),
            f"{ENVELOPE_SIGNAL}_peak": (
                [False, False, True, False, False, False]
                + [True, False, False, False, False, False]
            ),
        }
    )

    centered = centered_plateau_events(
        features,
        f"{ENVELOPE_SIGNAL}_peak",
    )

    assert centered == [3, 7]


def test_plateau_projection_preserves_raw_amplitude_and_event_count() -> None:
    sample = np.arange(1600)
    phase = sample % 400
    respiration = np.where(
        phase < 100,
        0.0,
        np.where(
            phase < 180,
            (phase - 100) / 80,
            np.where(
                phase < 260,
                1.0,
                np.where(phase < 340, 1 - (phase - 260) / 80, 0.0),
            ),
        ),
    )
    observations = pd.DataFrame(
        {"subject": 1, "respiration": respiration}
    )

    leading, leading_events = native_envelope_objects(observations)
    plateau, plateau_events = native_envelope_objects(
        observations,
        plateau_midpoints=True,
    )

    assert len(plateau_events) == len(leading_events)
    assert_series_equal(
        plateau["full_excursion"],
        leading["full_excursion"],
    )
    assert "peak_transition_index" in plateau
    assert "peak_detection_index" in plateau
