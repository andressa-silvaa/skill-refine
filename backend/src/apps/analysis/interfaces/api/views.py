"""
Compatibility facade for analysis API views.

Split by responsibility:
- rewrite_views.py
- analysis_views.py
"""
from __future__ import annotations

from .analysis_views import HistoryAnalysisView, LatestAnalysisView, RunAnalysisView
from .rewrite_views import (
    AIProviderError,
    AIUnavailableError,
    AiRewriteView,
    RateLimitExceeded,
    RewriteResult,
    rewrite_text_orchestrated,
)

__all__ = [
    "AIProviderError",
    "AIUnavailableError",
    "AiRewriteView",
    "HistoryAnalysisView",
    "LatestAnalysisView",
    "RateLimitExceeded",
    "RewriteResult",
    "RunAnalysisView",
    "rewrite_text_orchestrated",
]
