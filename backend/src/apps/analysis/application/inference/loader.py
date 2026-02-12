"""
Singleton loader for model/tokenizer. Thread-safe, load once per process.
Supports TF-IDF (sklearn) for seniority; HuggingFace when configured.
"""
from __future__ import annotations

import logging
import pickle
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
_lock = threading.Lock()

SENIORITY_LABELS = ("intern", "junior", "mid", "senior")


def _load_tfidf(path: Path) -> tuple[Any, list[str]]:
    """Load TF-IDF + LogReg pipeline from pickle."""
    with open(path, "rb") as f:
        data = pickle.load(f)
    pipeline = data.get("pipeline")
    labels = data.get("labels", list(SENIORITY_LABELS))
    if pipeline is None:
        raise ValueError("Invalid TF-IDF model: no pipeline")
    return pipeline, labels


def get_model_bundle(
    task: str = "seniority",
    language_mode: str = "mono",
    config: dict | None = None,
):
    """
    Return (model_or_pipeline, extra) for the given task.
    For seniority: returns (sklearn Pipeline, labels).
    Thread-safe singleton; loads once per process.
    """
    if config is None:
        from django.conf import settings
        config = __import__("apps.analysis.application.inference.config", fromlist=["get_config"]).get_config(settings)

    cache_key = f"{task}_{language_mode}"
    with _lock:
        if cache_key in _cache:
            return _cache[cache_key]

        if task == "seniority":
            path = config.get("tfidf_model_path") or config.get("model_dir", Path()) / "tfidf_logreg_seniority.pkl"
            path = Path(path)
            if not path.exists():
                logger.warning("TF-IDF model not found at %s; seniority will use heuristics", path)
                _cache[cache_key] = (None, list(SENIORITY_LABELS))
                return _cache[cache_key]
            try:
                pipeline, labels = _load_tfidf(path)
                _cache[cache_key] = (pipeline, labels)
                logger.info("Loaded seniority model from %s", path)
                return _cache[cache_key]
            except Exception as e:
                logger.warning("Failed to load TF-IDF model: %s; falling back to heuristics", e)
                _cache[cache_key] = (None, list(SENIORITY_LABELS))
                return _cache[cache_key]

        _cache[cache_key] = (None, [])
        return _cache[cache_key]


def clear_cache() -> None:
    """Clear model cache (for tests)."""
    with _lock:
        _cache.clear()
