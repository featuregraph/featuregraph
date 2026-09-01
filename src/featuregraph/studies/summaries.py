"""Small descriptive-statistics helpers shared across study reports."""

from __future__ import annotations

import numpy as np
import pandas as pd


def finite_summary(values: pd.Series) -> dict[str, float | int]:
    """Summarize a series after dropping missing and infinite values.

    Used to report a measurement (period, rate, amplitude, ...) across a
    cohort without a stray ``inf`` or ``NaN`` silently corrupting the mean.
    """
    clean = values.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    return {
        "count": int(len(clean)),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "standard_deviation": float(clean.std()),
        "q25": float(clean.quantile(0.25)),
        "q75": float(clean.quantile(0.75)),
        "minimum": float(clean.min()),
        "maximum": float(clean.max()),
    }
