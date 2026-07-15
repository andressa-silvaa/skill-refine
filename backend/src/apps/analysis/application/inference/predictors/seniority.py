"""Compatibility shim — prefer ``inference.tasks.seniority.hf_predict``."""
from apps.analysis.application.inference.tasks.seniority.hf_predict import (  # noqa: F401
    SENIORITY_LABELS,
    predict_hf_seniority_probs,
)

__all__ = ["SENIORITY_LABELS", "predict_hf_seniority_probs"]
