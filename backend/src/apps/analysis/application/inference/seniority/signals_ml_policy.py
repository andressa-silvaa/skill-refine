"""Compatibility shim — prefer ``inference.tasks.seniority.signals_ml_policy``."""
from apps.analysis.application.inference.tasks.seniority.signals_ml_policy import (  # noqa: F401
    apply_signals_ml_gates,
    raw_argmax_label,
)

__all__ = ["apply_signals_ml_gates", "raw_argmax_label"]
