"""
Inference module for resume analysis: seniority, quality, insights.
Loads models once (singleton), runs in background (Celery/thread).
"""
from __future__ import annotations

from .orchestrator import analyze_resume

__all__ = ["analyze_resume"]
