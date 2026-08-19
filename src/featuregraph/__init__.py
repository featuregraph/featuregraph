"""
FeatureGraph public API.
"""

from . import datasets
from .behaviors import feature_object, transition
from .behaviors.state_occurrence import from_state_sequence
from .preprocessing.smoothing import smooth
from .utils._plot import plot

__version__ = "0.1.0a1"


__all__ = [
    "oscillation",
    "accumulation",
    "transition",
    "feature_object",
    "from_state_sequence",
    "datasets",
    "plot",
    "smooth",
]
