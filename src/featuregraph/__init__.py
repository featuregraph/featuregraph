"""
FeatureGraph public API.
"""

from . import datasets
from .behaviors import transition
from .utils._plot import plot
from .preprocessing.smoothing import smooth

__version__ = "0.1.0a1"

__all__ = [
    "oscillation",
    "accumulation",
    "transition",
    "datasets",
    "plot",
    "smooth"
]
