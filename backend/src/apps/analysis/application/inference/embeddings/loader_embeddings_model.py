"""Compatibility shim — prefer ``inference.tasks.target_fit.loader_embeddings``."""
from apps.analysis.application.inference.tasks.target_fit.loader_embeddings import (  # noqa: F401
    clear_embeddings_cache,
    get_embeddings_model,
)

__all__ = ["clear_embeddings_cache", "get_embeddings_model"]
