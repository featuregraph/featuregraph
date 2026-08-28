"""
FeatureGraph public API.
"""

from . import datasets
from .behaviors import feature_object, transition
from .behaviors.state_occurrence import from_state_sequence
from .contracts import (
    ApprovedStudyContract,
    CompiledStateResult,
    StateContractError,
    StudyContractApprovalError,
    approve_study_contract,
    canonical_study_contract,
    compile_states,
    load_approved_study_contract,
    study_contract_differences,
    study_contract_payload,
    study_contract_sha256,
)
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
    "ApprovedStudyContract",
    "StudyContractApprovalError",
    "StateContractError",
    "approve_study_contract",
    "canonical_study_contract",
    "compile_states",
    "load_approved_study_contract",
    "study_contract_differences",
    "study_contract_payload",
    "study_contract_sha256",
]
