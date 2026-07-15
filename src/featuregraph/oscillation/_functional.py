# src/featuregraph/oscillation/_functional.py

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from featuregraph.oscillation.waves import (
    add_wave_features,
    add_wave_id,
    add_wave_primitives,
    add_wave_smoothing,
    get_wave_summary,
)


def oscillate(
    X: pd.Series | pd.DataFrame,
    *,
    signal: str | None = None,
    group: Sequence[str] | None = None,
    smooth: bool = False,
) -> pd.DataFrame:
    """
    Construct explicit oscillation objects from an observation sequence.

    Parameters
    ----------
    X
        A signal represented as a pandas Series, or a DataFrame containing
        the signal and optional grouping columns.
    signal
        Name of the signal column when ``X`` is a DataFrame.
    group
        Columns defining independent observation sequences.
    smooth
        Whether to smooth the signal before oscillation construction.

    Returns
    -------
    pandas.DataFrame
        One row per constructed oscillation.
    """
    if isinstance(X, pd.Series):
        signal_name = X.name or "signal"
        df = X.rename(signal_name).to_frame()
    elif isinstance(X, pd.DataFrame):
        if signal is None:
            raise ValueError(
                "`signal` must be provided when X is a DataFrame."
            )
        signal_name = signal
        df = X.copy()
    else:
        raise TypeError(
            "X must be a pandas Series or pandas DataFrame."
        )

    group_columns = list(group or [])

    working_signal = signal_name

    if smooth:
        df = add_wave_smoothing(
            df,
            [signal_name],
            group_columns,
        )
        working_signal = f"{signal_name}_smooth"

    df = add_wave_primitives(
        df,
        [working_signal],
    )

    df = add_wave_id(
        df,
        [working_signal],
        group_columns,
    )

    wave_group = [
        *group_columns,
        f"{working_signal}_wave_id",
    ]

    df = add_wave_features(
        df,
        [working_signal],
        wave_group,
    )

    return get_wave_summary(
        df,
        working_signal,
    )