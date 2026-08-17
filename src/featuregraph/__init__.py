"""
FeatureGraph public API.
"""

from . import datasets
from .behaviors import accumulation, oscillation
from .utils._plot import plot

__version__ = "0.1.0b1"

__all__ = [
    "oscillation",
    "accumulation",
    "datasets",
    "plot",
]
