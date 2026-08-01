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
    """Load one Tennessee Eastman simulation run.

    Parameters
    ----------
    dataset:
        ``"faulty_training"`` for a selected fault run or
        ``"faultfree_training"`` for the normal-operation training
        workbook. ``"fault_free_training"`` is accepted as an alias.

    fault_number:
        Fault identifier for ``faulty_training``. It is accepted but
        ignored for ``faultfree_training``; fault-free rows are labeled
        with fault number zero.

    simulation_run:
        Simulation-run identifier added to the returned frame.

    refresh:
        Redownload the source workbook even when it is cached.

    Returns
    -------
    pandas.DataFrame
        Industrial process observations with standardized FeatureGraph
        column names.
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
