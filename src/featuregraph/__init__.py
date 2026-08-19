"""
FeatureGraph public API.
"""

from . import datasets
from .behaviors import transition, feature_object
from .utils._plot import plot
from .preprocessing.smoothing import smooth


__version__ = "0.1.0a1"


__all__ = [
    "oscillation",
    "accumulation",
    "transition",
    "feature_object",
    "datasets",
    "plot",
    "smooth"
]
