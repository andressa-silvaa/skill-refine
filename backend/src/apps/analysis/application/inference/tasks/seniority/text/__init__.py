"""Text-based seniority: embedding probe with lexical fallback."""
from __future__ import annotations

from .loader_seniority_probe import get_seniority_probe_bundle
from .predict import predict_text_seniority

__all__ = [
    "get_seniority_probe_bundle",
    "predict_text_seniority",
]
