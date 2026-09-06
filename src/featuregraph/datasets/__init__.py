"""
FeatureGraph example datasets.
"""

from ._bidmc import bidmc, bidmc_breaths
from ._capnobase import CAPNOBASE_CASES, capnobase, capnobase_labels
from ._cartpole import cartpole
from ._eastman import eastman
from ._mountaincar import mountaincar

__all__ = [
    "bidmc",
    "bidmc_breaths",
    "CAPNOBASE_CASES",
    "capnobase",
    "capnobase_labels",
    "cartpole",
    "eastman",
    "mountaincar",
]
