"""Compatibility shim — prefer ``inference.tasks.target_fit.loader_ml``."""
from apps.analysis.application.inference.tasks.target_fit.loader_ml import (  # noqa: F401
    clear_target_fit_ml_cache,
    get_target_fit_ml_bundle,
    predict_target_fit_ml_score,
    target_fit_ml_metadata_for_task,
)

__all__ = [
    "clear_target_fit_ml_cache",
    "get_target_fit_ml_bundle",
    "predict_target_fit_ml_score",
    "target_fit_ml_metadata_for_task",
]
