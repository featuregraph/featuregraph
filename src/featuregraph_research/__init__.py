"""
FeatureGraph public API.
"""

# from .behaviors import oscillation, accumulation
from .constructors import primitives
from . import datasets

from .utils._plot import plot

__version__ = "0.1.0"

__all__ = [
    # "oscillation",
    # "accumulation",
    "primitives",
    "datasets",
    "plot",
]