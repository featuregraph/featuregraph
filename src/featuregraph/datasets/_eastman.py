from __future__ import annotations

import pandas as pd

from featuregraph.utils._eastman import load_tep_run
from featuregraph.utils._rename_map import eastman_map


def eastman(
    *,
    dataset: str = "faulty_training",
    fault_number: int = 1,
    simulation_run: int = 1,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Load one Tennessee Eastman simulation run.

    Returns
    -------
    pandas.DataFrame
        Industrial process observations with standardized
        FeatureGraph column names.
    """
    return (
        load_tep_run(
            dataset,
            fault_number=fault_number,
            simulation_run=simulation_run,
            refresh=refresh,
        )
        .rename(columns=eastman_map)
    )