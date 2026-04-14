"""Text-based seniority (neural + lexical fallback) and fusion with structured signals."""
from __future__ import annotations

from .fuse_seniority import fuse_seniority
from .predict import predict_text_seniority

__all__ = ["fuse_seniority", "predict_text_seniority"]
