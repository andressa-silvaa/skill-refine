"""Text-based seniority (embedding probe, HF bundle, lexical fallback) and fusion with signals."""
from __future__ import annotations

from .fuse_seniority import fuse_seniority, structural_signals_strength
from .loader_seniority_probe import get_seniority_probe_bundle
from .loader_text_seniority_model import get_text_seniority_bundle
from .predict import predict_text_seniority

__all__ = [
    "fuse_seniority",
    "get_seniority_probe_bundle",
    "get_text_seniority_bundle",
    "predict_text_seniority",
    "structural_signals_strength",
]
