"""
Singleton loader for model/tokenizer. Thread-safe, load once per process.
Supports: HuggingFace (HF) from ml/models/<version>/hf, TF-IDF (legacy), heuristics fallback.

A resolução de caminho e a leitura dos artefatos vivem em ``loader_artifacts.py`` e são
reexportadas aqui: ``_metadata_supports_task`` é importado dos testes a partir deste módulo.
"""
from __future__ import annotations

import json
import logging
import pickle
import threading
from pathlib import Path
from typing import Any

from .loader_artifacts import (
    SENIORITY_LABELS,
    _MatchingBiEncoderWithProjection,
    _load_hf_seniority,
    _load_metadata,
    _load_tfidf,
    _metadata_supports_task,
    _resolve_model_dir,
    _resolve_model_path,
)

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
_lock = threading.Lock()


def get_model_bundle(
    task: str = "seniority",
    language_mode: str = "mono",
    language: str = "pt-BR",
    config: dict | None = None,
):
    """
    Return (model_or_pipeline, extra) for the given task.
    For seniority: (model/tokenizer/pipeline, {labels, metadata, provider}).
    Thread-safe singleton; loads once per process.
    """
    if config is None:
        from django.conf import settings
        from .config import get_config
        config = get_config(settings)

    cache_key = f"{task}_{language_mode}_{language}"
    with _lock:
        if cache_key in _cache:
            return _cache[cache_key]

        allow_fallback = config.get("allow_heuristics_fallback", True)
        model_mode = config.get("model_mode", "hf")

        if task == "seniority":
            hf_path, model_version, metadata = _resolve_model_path(config, language, task="seniority")

            if hf_path and model_mode in ("hf", "onnx"):
                if not _metadata_supports_task(metadata, "seniority"):
                    logger.info(
                        "Skipping HF seniority model from %s due to metadata task mismatch: %s",
                        hf_path,
                        metadata.get("task"),
                    )
                else:
                    try:
                        model, tokenizer, meta = _load_hf_seniority(hf_path)
                        extra = {
                            "labels": list(SENIORITY_LABELS),
                            "metadata": {**metadata, **meta},
                            "provider": "local",
                            "tokenizer": tokenizer,
                        }
                        _cache[cache_key] = (model, extra)
                        logger.info("Loaded HF seniority model from %s", hf_path)
                        return _cache[cache_key]
                    except Exception as e:
                        logger.warning("Failed to load HF seniority model: %s", e)
                        if not allow_fallback:
                            raise

            tfidf_path = config.get("tfidf_model_path") or Path(config.get("model_dir", "")) / "tfidf_logreg_seniority.pkl"
            tfidf_path = Path(tfidf_path) if tfidf_path else Path()
            if tfidf_path.exists():
                try:
                    pipeline, labels = _load_tfidf(tfidf_path)
                    extra = {"labels": labels, "metadata": metadata, "provider": "tfidf"}
                    _cache[cache_key] = (pipeline, extra)
                    logger.info("Loaded TF-IDF seniority model from %s", tfidf_path)
                    return _cache[cache_key]
                except Exception as e:
                    logger.warning("Failed to load TF-IDF model: %s", e)

            if not allow_fallback:
                raise RuntimeError(
                    "Analysis model not available and heuristics fallback disabled. "
                    "Set ANALYSIS_ALLOW_HEURISTICS_FALLBACK=true in dev or deploy a model to ml/models/."
                )
            _cache[cache_key] = (None, {"labels": list(SENIORITY_LABELS), "metadata": {}, "provider": "heuristics-only"})
            logger.warning("Using heuristics-only for seniority (no model loaded)")
            return _cache[cache_key]

        _cache[cache_key] = (None, [])
        return _cache[cache_key]


def get_quality_bundle(language: str = "pt-BR", config: dict | None = None) -> tuple[Any, dict]:
    """Load quality model if available. Returns (model_or_none, {metadata, provider})."""
    if config is None:
        from django.conf import settings
        from .config import get_config
        config = get_config(settings)

    cache_key = f"quality_{language}"
    with _lock:
        if cache_key in _cache:
            return _cache[cache_key]

        if config.get("model_mode") == "heuristics":
            _cache[cache_key] = (None, {"metadata": {}, "provider": "heuristics-only"})
            return _cache[cache_key]

        model_dir, _, metadata = _resolve_model_dir(config, language, task="quality")
        hybrid_path = model_dir / "hybrid" / "model.pkl"
        if hybrid_path.exists():
            if not _metadata_supports_task(metadata, "quality"):
                logger.info(
                    "Skipping hybrid quality model from %s due to metadata task mismatch: %s",
                    hybrid_path,
                    metadata.get("task"),
                )
            else:
                try:
                    with open(hybrid_path, "rb") as f:
                        hybrid_bundle = pickle.load(f)
                    extra = {"metadata": metadata, "provider": metadata.get("provider", "hybrid-local"), "kind": "hybrid"}
                    _cache[cache_key] = (hybrid_bundle, extra)
                    return _cache[cache_key]
                except Exception as e:
                    logger.warning("Failed to load hybrid quality model: %s", e)

        hf_path, model_version, metadata = _resolve_model_path(config, language, task="quality")
        if hf_path and config.get("model_mode") in ("hf", "onnx"):
            if not _metadata_supports_task(metadata, "quality"):
                logger.info(
                    "Skipping HF quality model from %s due to metadata task mismatch: %s",
                    hf_path,
                    metadata.get("task"),
                )
            else:
                try:
                    from transformers import AutoModelForSequenceClassification, AutoTokenizer
                    tokenizer = AutoTokenizer.from_pretrained(str(hf_path))
                    model = AutoModelForSequenceClassification.from_pretrained(str(hf_path))
                    model.eval()
                    extra = {"metadata": metadata, "provider": "local", "tokenizer": tokenizer}
                    _cache[cache_key] = (model, extra)
                    return _cache[cache_key]
                except Exception as e:
                    logger.warning("Failed to load quality model: %s", e)

        _cache[cache_key] = (None, {"metadata": {}, "provider": "heuristics-only"})
        return _cache[cache_key]


def get_matching_bundle(language: str = "pt-BR", config: dict | None = None) -> tuple[Any, dict]:
    """Load matching (bi-encoder) model if available. Returns (model_or_none, {metadata, provider})."""
    if config is None:
        from django.conf import settings
        from .config import get_config
        config = get_config(settings)

    cache_key = f"matching_{language}"
    with _lock:
        if cache_key in _cache:
            return _cache[cache_key]

        if config.get("model_mode") == "heuristics":
            _cache[cache_key] = (None, {"metadata": {}, "provider": "heuristics-only"})
            return _cache[cache_key]

        model_dir, _, metadata = _resolve_model_dir(config, language, task="matching")
        matching_dir = model_dir / "matching"
        if (matching_dir / "model.pt").exists():
            if not _metadata_supports_task(metadata, "matching"):
                logger.info(
                    "Skipping matching model from %s due to metadata task mismatch: %s",
                    matching_dir,
                    metadata.get("task"),
                )
            else:
                try:
                    import torch
                    from transformers import AutoModel, AutoTokenizer

                    encoder_dir = matching_dir / "encoder"
                    bundle_cfg_path = matching_dir / "matching_config.json"
                    bundle_cfg = {}
                    if bundle_cfg_path.exists():
                        with open(bundle_cfg_path, encoding="utf-8") as f:
                            bundle_cfg = json.load(f)
                    tokenizer = AutoTokenizer.from_pretrained(str(encoder_dir))
                    encoder = AutoModel.from_pretrained(str(encoder_dir))
                    model = _MatchingBiEncoderWithProjection(
                        encoder,
                        hidden_size=int(bundle_cfg.get("hidden_size", getattr(encoder.config, "hidden_size", 768))),
                        dropout=float(bundle_cfg.get("dropout", 0.1)),
                        blend_alpha=float(bundle_cfg.get("blend_alpha", 0.65)),
                    )
                    state = torch.load(matching_dir / "model.pt", map_location="cpu")
                    model.load_state_dict(state)
                    model.eval()
                    extra = {
                        "metadata": metadata,
                        "provider": "local",
                        "tokenizer": tokenizer,
                        "kind": "matching-biencoder",
                    }
                    _cache[cache_key] = (model, extra)
                    return _cache[cache_key]
                except Exception as e:
                    logger.warning("Failed to load matching bi-encoder model: %s", e)

        hf_path, _, metadata = _resolve_model_path(config, language, task="matching")
        if hf_path and config.get("model_mode") in ("hf", "onnx"):
            if not _metadata_supports_task(metadata, "matching"):
                logger.info(
                    "Skipping HF matching model from %s due to metadata task mismatch: %s",
                    hf_path,
                    metadata.get("task"),
                )
            else:
                try:
                    from transformers import AutoModel, AutoTokenizer
                    tokenizer = AutoTokenizer.from_pretrained(str(hf_path))
                    model = AutoModel.from_pretrained(str(hf_path))
                    model.eval()
                    extra = {"metadata": metadata, "provider": "local", "tokenizer": tokenizer}
                    _cache[cache_key] = (model, extra)
                    return _cache[cache_key]
                except Exception as e:
                    logger.warning("Failed to load matching model: %s", e)

        _cache[cache_key] = (None, {"metadata": {}, "provider": "heuristics-only"})
        return _cache[cache_key]


def clear_cache() -> None:
    """Clear model cache (for tests)."""
    with _lock:
        _cache.clear()
