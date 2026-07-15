"""Compatibility shim — prefer ``inference.tasks.target_fit``."""

from apps.analysis.application.inference.tasks.target_fit import (  # noqa: F401
    TARGET_FIT_POLICY_VERSION,
    TargetFitSignals,
    compute_career_switch,
    compute_target_fit_policy,
    compute_target_seniority,
    extract_target_fit_signals,
    heuristic_target_fit_score,
    infer_domain_category,
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
