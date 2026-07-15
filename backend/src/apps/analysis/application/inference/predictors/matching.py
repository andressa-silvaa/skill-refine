"""Compatibility shim — prefer ``inference.tasks.matching.predict``."""
from apps.analysis.application.inference.tasks.matching.predict import predict_matching  # noqa: F401

__all__ = ["predict_matching"]
