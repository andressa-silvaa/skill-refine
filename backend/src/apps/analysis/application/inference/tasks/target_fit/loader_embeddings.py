"""
Singleton SentenceTransformer loader (optional dependency).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_model: Any = None
_model_key: str = ""
_st_import_failed: bool = False


def _enabled(settings) -> bool:
    return bool(getattr(settings, "ANALYSIS_EMBEDDINGS_ENABLED", False))


def get_embeddings_model(settings):
    global _model, _model_key, _st_import_failed
    if not _enabled(settings):
        return None
    if _st_import_failed:
        return None
    name = str(getattr(settings, "ANALYSIS_EMBEDDINGS_MODEL_NAME", "") or "").strip()
    if not name:
        name = "paraphrase-multilingual-MiniLM-L12-v2"
    if _model is not None and _model_key == name:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        _st_import_failed = True
        logger.warning(
            "embeddings: sentence-transformers not importable (%s). "
            "Run: pip install sentence-transformers (same env as Django). Disabling embeddings for this process.",
            exc,
        )
        _model, _model_key = None, name
        return None
    try:
        m = SentenceTransformer(name)
        _model = m
        _model_key = name
        logger.info("embeddings: loaded %s", name)
        return _model
    except Exception as exc:
        logger.warning(
            "embeddings: failed to load %s (%s). Try WSL/Linux or pre-download model.",
            name,
            exc,
        )
        _model, _model_key = None, name
        return None


def clear_embeddings_cache() -> None:
    global _model, _model_key, _st_import_failed
    _model = None
    _model_key = ""
    _st_import_failed = False
