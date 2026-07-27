"""
FeatureGraph public API.
"""

from . import datasets
from .behaviors import accumulation, oscillation, transition
from .utils._plot import plot

__version__ = "0.1.0a1"

__all__ = [
    "oscillation",
    "accumulation",
    "transition",
    "datasets",
    "plot",
]
