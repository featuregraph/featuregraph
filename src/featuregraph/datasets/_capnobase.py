from __future__ import annotations

import pandas as pd

from featuregraph.utils._capnobase import (
    CAPNOBASE_CASES,
    load_capnobase_labels,
    load_capnobase_signals,
)


def capnobase(
    case: str | int = "0009",
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load the capnogram, PPG, and ECG waveforms for one CapnoBase case."""
    return load_capnobase_signals(case, refresh=refresh)


def capnobase_labels(
    case: str | int = "0009",
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load expert pulse, breath, and artifact labels for one case."""
    return load_capnobase_labels(case, refresh=refresh)


__all__ = ["CAPNOBASE_CASES", "capnobase", "capnobase_labels"]
