"""Compatibility shim — prefer ``inference.tasks.seniority.signals_ml_predict``."""
from apps.analysis.application.inference.tasks.seniority.signals_ml_predict import (  # noqa: F401
    signals_ml_predict,
)

__all__ = ["signals_ml_predict"]
