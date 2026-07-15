"""Compatibility shim — prefer ``inference.tasks.seniority.text``."""
from __future__ import annotations

from apps.analysis.application.inference.tasks.seniority.text import (  # noqa: F401
    fuse_seniority,
    predict_text_seniority,
)

__all__ = ["fuse_seniority", "predict_text_seniority"]
