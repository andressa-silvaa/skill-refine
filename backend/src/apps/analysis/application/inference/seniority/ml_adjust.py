"""Compatibility shim — prefer ``inference.tasks.seniority.ml_adjust``."""
from apps.analysis.application.inference.tasks.seniority.ml_adjust import ml_adjust_seniority  # noqa: F401

__all__ = ["ml_adjust_seniority"]
