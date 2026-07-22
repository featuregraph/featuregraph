import pandas as pd
import pytest


@pytest.fixture
def triangular_signal() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "signal": [
                0.0,
                1.0,
                2.0,
                1.0,
                0.0,
                1.0,
                2.0,
                1.0,
                0.0,
                1.0,
                2.0,
                1.0,
                0.0,
            ]
        }
    )


@pytest.fixture
def grouped_triangular_signal() -> pd.DataFrame:
    values = [0.0, 1.0, 2.0, 1.0, 0.0] * 2
    return pd.DataFrame(
        {
            "subject": ["a"] * 5 + ["b"] * 5,
            "run": [1] * 10,
            "signal": values,
            "signal_2": [value * 2 for value in values],
        }
    )
