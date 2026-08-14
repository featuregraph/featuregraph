from __future__ import annotations

import pandas as pd

from featuregraph.utils._bidmc import (
    load_bidmc_breaths,
    load_bidmc_subject,
)
from featuregraph.utils._rename_map import bidmc_map


def bidmc(
    subject: int = 1,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Load one BIDMC subject.

    Returns
    -------
    pandas.DataFrame
        Physiological waveform observations with standardized
        FeatureGraph column names.
    """
    return (
        load_bidmc_subject(
            subject,
            refresh=refresh,
        )
        .rename(columns=bidmc_map)
    )


def bidmc_breaths(
    subject: int = 1,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load the two BIDMC breath-annotation columns for one subject."""
    return load_bidmc_breaths(
        subject,
        refresh=refresh,
    )
