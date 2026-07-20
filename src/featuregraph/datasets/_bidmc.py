from __future__ import annotations

import pandas as pd

from featuregraph.utils.bidmc import load_bidmc_subject
from featuregraph.utils.rename_map import bidmc_map


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