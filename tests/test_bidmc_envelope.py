import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_series_equal

from experiments.bidmc_llm_capture.native_envelope import (
    ENVELOPE_SIGNAL,
    add_respiration_envelope,
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
