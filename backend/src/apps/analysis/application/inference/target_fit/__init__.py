"""Target role fit: domain inference, structural signals, conservative target seniority."""

from .domain_inference import infer_domain_category
from .fit_signals import TargetFitSignals, extract_target_fit_signals
from .target_seniority import (
    TARGET_FIT_POLICY_VERSION,
    compute_career_switch,
    compute_target_fit_policy,
    compute_target_seniority,
    heuristic_target_fit_score,
)

__all__ = [
    "TARGET_FIT_POLICY_VERSION",
    "TargetFitSignals",
    "compute_career_switch",
    "compute_target_fit_policy",
    "compute_target_seniority",
    "extract_target_fit_signals",
    "heuristic_target_fit_score",
    "infer_domain_category",
]
