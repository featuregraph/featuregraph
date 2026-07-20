"""
FeatureGraph public API.
"""

from .behaviors import oscillation, accumulation
from . import datasets

__version__ = "0.1.0"

__all__ = [
    "oscillation",
    "accumulation",
    "datasets",
]