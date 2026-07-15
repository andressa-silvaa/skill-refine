"""Compatibility shim — prefer ``inference.tasks.seniority.text.predict``."""
from apps.analysis.application.inference.tasks.seniority.text.predict import (  # noqa: F401
    predict_text_seniority,
)

__all__ = ["predict_text_seniority"]
