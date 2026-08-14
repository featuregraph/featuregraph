import numpy as np
import pytest

from experiments.bidmc_llm_capture.reproduce_llm_method import (
    assemble_objects,
)


def test_assemble_objects_applies_complete_and_partial_contracts() -> None:
    signal = np.array([0, 0, 2, 0, 0, 3, 0, 0, 4, 2], dtype=float)
    peaks = np.array([2, 5, 8])
    troughs = np.array([1, 4, 7])

    result = assemble_objects(
        signal,
        peaks,
        troughs,
        sampling_rate=2,
    )

    assert result["is_complete"].tolist() == [True, True, False]
    assert result["start_index"].tolist() == [1, 4, 7]
    assert result["peak_index"].tolist() == [2, 5, 8]
    assert result["end_index"].tolist() == [4, 7, 9]
    assert np.isnan(result.loc[0, "period_seconds"])
    assert result.loc[1, "period_seconds"] == 1.5
    assert result.loc[0, "full_excursion"] == 2
    assert result.loc[0, "temporal_symmetry"] == pytest.approx(2 / 3)
