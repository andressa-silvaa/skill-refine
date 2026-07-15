"""Compatibility shim — prefer ``inference.tasks.target_fit.fit_signals``."""
from apps.analysis.application.inference.tasks.target_fit.fit_signals import (  # noqa: F401
    TargetFitSignals,
    extract_target_fit_signals,
)

__all__ = ["TargetFitSignals", "extract_target_fit_signals"]
