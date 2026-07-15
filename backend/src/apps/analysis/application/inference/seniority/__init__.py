"""Compatibility shim — prefer ``inference.tasks.seniority``."""
from apps.analysis.application.inference.tasks.seniority.ml_adjust import ml_adjust_seniority
from apps.analysis.application.inference.tasks.seniority.rule_based import (
    clamp_seniority_vetoes,
    rule_based_seniority,
)

__all__ = ["clamp_seniority_vetoes", "ml_adjust_seniority", "rule_based_seniority"]
