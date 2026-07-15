"""Compatibility shim — prefer ``inference.tasks.seniority.text.loader_text_seniority_model``."""
from apps.analysis.application.inference.tasks.seniority.text.loader_text_seniority_model import (  # noqa: F401
    get_text_seniority_bundle,
)

__all__ = ["get_text_seniority_bundle"]
