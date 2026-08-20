"""
FeatureGraph public API.
"""

from . import datasets
from .behaviors import feature_object, transition
from .behaviors.state_occurrence import from_state_sequence
from .contracts import CompiledStateResult, StateContractError, compile_states
from .preprocessing.smoothing import smooth
from .utils._plot import plot

__version__ = "0.1.0a1"


__all__ = [
    "transition",
    "feature_object",
    "from_state_sequence",
    "datasets",
    "plot",
    "smooth",
    "CompiledStateResult",
    "StateContractError",
    "compile_states",
]
