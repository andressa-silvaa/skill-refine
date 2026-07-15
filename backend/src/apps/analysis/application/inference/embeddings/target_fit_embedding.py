"""Compatibility shim — prefer ``inference.tasks.target_fit.embedding``."""
from apps.analysis.application.inference.tasks.target_fit.embedding import (  # noqa: F401
    build_cv_embedding_text,
    build_target_embedding_text,
    compute_semantic_keyword_evidence,
    embedding_fit_scores,
)

__all__ = [
    "build_cv_embedding_text",
    "build_target_embedding_text",
    "compute_semantic_keyword_evidence",
    "embedding_fit_scores",
]
