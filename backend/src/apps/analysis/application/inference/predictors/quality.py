"""Compatibility shim — prefer ``inference.tasks.quality.predict``."""
from apps.analysis.application.inference.tasks.quality.predict import *  # noqa: F401,F403
from apps.analysis.application.inference.tasks.quality.predict import predict_quality  # noqa: F401

__all__ = ["predict_quality"]
