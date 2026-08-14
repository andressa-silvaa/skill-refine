"""
Compatibility shim — prefer ``inference.tasks.target_fit.loader_ml``.

A shim that re-exports only part of the module it stands in for is worse than no shim: the import
fails at collection time, so every test in the importing module disappears rather than failing
loudly. ``load_target_fit_ml_bundle`` was missing here for exactly that reason.
"""
from apps.analysis.application.inference.tasks.target_fit.loader_ml import (  # noqa: F401
    clear_target_fit_ml_cache,
    get_target_fit_ml_bundle,
    load_target_fit_ml_bundle,
    predict_target_fit_ml_score,
    target_fit_ml_metadata_for_task,
)

__all__ = [
    "clear_target_fit_ml_cache",
    "get_target_fit_ml_bundle",
    "load_target_fit_ml_bundle",
    "predict_target_fit_ml_score",
    "target_fit_ml_metadata_for_task",
]
