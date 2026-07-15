"""Compatibility shim — prefer ``inference.tasks.seniority.rule_based``."""
from apps.analysis.application.inference.tasks.seniority.rule_based import (  # noqa: F401
    clamp_seniority_vetoes,
    rule_based_seniority,
)

__all__ = ["clamp_seniority_vetoes", "rule_based_seniority"]
