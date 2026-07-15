"""Compatibility shim — prefer ``inference.tasks.seniority.text.fuse_seniority``."""
from apps.analysis.application.inference.tasks.seniority.text.fuse_seniority import (  # noqa: F401
    fuse_seniority,
    structural_signals_strength,
)

__all__ = ["fuse_seniority", "structural_signals_strength"]
