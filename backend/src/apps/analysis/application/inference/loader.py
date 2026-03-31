"""
Singleton loader for model/tokenizer. Thread-safe, load once per process.
Supports: HuggingFace (HF) from ml/models/<version>/hf, TF-IDF (legacy), heuristics fallback.
"""
from __future__ import annotations

import json
import logging
import pickle
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
_lock = threading.Lock()

SENIORITY_LABELS = ("intern", "junior", "mid", "senior")


class _MatchingBiEncoderWithProjection:
    """Lazy wrapper around the custom matching bi-encoder artifact."""

    def __init__(self, encoder, hidden_size: int, dropout: float = 0.1, blend_alpha: float = 0.65):
        import torch

        self._torch = torch
        self.encoder = encoder
        self.hidden_size = hidden_size
        self.blend_alpha = float(blend_alpha)
        self.proj = torch.nn.Sequential(
            torch.nn.Linear(hidden_size * 2, hidden_size),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout),
            torch.nn.Linear(hidden_size, 1),
        )

    def load_state_dict(self, state_dict):
        self.proj.load_state_dict({k.replace("proj.", "", 1): v for k, v in state_dict.items() if k.startswith("proj.")}, strict=True)
        encoder_state = {k.replace("encoder.", "", 1): v for k, v in state_dict.items() if k.startswith("encoder.")}
        self.encoder.load_state_dict(encoder_state, strict=False)

    def eval(self):
        self.encoder.eval()
        self.proj.eval()
        return self

    def __call__(self, job_input_ids, job_attention_mask, resume_input_ids, resume_attention_mask):
        F = self._torch.nn.functional
        job_out = self.encoder(input_ids=job_input_ids, attention_mask=job_attention_mask)
        resume_out = self.encoder(input_ids=resume_input_ids, attention_mask=resume_attention_mask)
        job_pooled = job_out.last_hidden_state[:, 0]
        resume_pooled = resume_out.last_hidden_state[:, 0]
        cos = F.cosine_similarity(job_pooled.unsqueeze(1), resume_pooled.unsqueeze(0), dim=-1).diag()
        concat = self._torch.cat([job_pooled, resume_pooled], dim=-1)
        score = self.proj(concat).squeeze(-1)
        score = self._torch.sigmoid(score)
        return (self.blend_alpha * score) + ((1.0 - self.blend_alpha) * ((cos + 1.0) / 2.0))


def _load_metadata(model_dir: Path) -> dict:
    """Load metadata.json from model dir (parent of hf/)."""
    meta_path = model_dir / "metadata.json"
    if not meta_path.exists():
        meta_path = (model_dir / ".." / "metadata.json").resolve()
    if not meta_path.exists():
        return {}
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f)


def _metadata_supports_task(metadata: dict, task: str) -> bool:
    """Return True when metadata declares a compatible task for the requested bundle."""
    meta_task = str((metadata or {}).get("task") or "").strip().lower()
    requested = str(task or "").strip().lower()
    if not meta_task:
        return True
    if meta_task in {requested, "multitask"}:
        return True
    return meta_task.startswith(f"{requested}-")


def _load_hf_seniority(hf_dir: Path) -> tuple[Any, Any, dict]:
    """Load HF model + tokenizer for seniority. Returns (model, tokenizer, metadata)."""
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError:
        raise RuntimeError("transformers required for HF mode; install: pip install transformers torch")
    tokenizer = AutoTokenizer.from_pretrained(str(hf_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(hf_dir))
    model.eval()
    meta_dir = hf_dir.parent if hf_dir.name == "hf" else hf_dir
    metadata = _load_metadata(meta_dir)
    return model, tokenizer, metadata


def _load_tfidf(path: Path) -> tuple[Any, list[str]]:
    """Load TF-IDF + LogReg pipeline from pickle."""
    with open(path, "rb") as f:
        data = pickle.load(f)
    pipeline = data.get("pipeline")
    labels = data.get("labels", list(SENIORITY_LABELS))
    if pipeline is None:
        raise ValueError("Invalid TF-IDF model: no pipeline")
    return pipeline, labels


def _resolve_model_dir(config: dict, language: str, task: str = "seniority") -> tuple[Path, str, dict]:
    model_root = Path(config.get("model_root", config.get("model_dir", Path())))
    version_by_lang = config.get("model_version_by_lang") or {}
    version_by_task = config.get("model_version_by_task") or {}
    version_by_task_lang = config.get("model_version_by_task_lang") or {}
    model_version = (
        version_by_task_lang.get(f"{task}:{language}")
        or version_by_task_lang.get(f"{task}:{language.strip()}")
        or version_by_task.get(task)
        or version_by_lang.get(language)
        or config.get("model_version", "analysis_v1_pt")
    )
    model_dir = model_root / model_version
    metadata = _load_metadata(model_dir)
    metadata.setdefault("model_version", model_version)
    metadata.setdefault("dataset_version", "unknown")
    metadata.setdefault("languages_supported", [])
    metadata.setdefault("provider", "local")
    return model_dir, model_version, metadata


def _resolve_model_path(config: dict, language: str, task: str = "seniority") -> tuple[Path | None, str, dict]:
    """
    Resolve model path for given language.
    Returns (hf_path_or_none, model_version, metadata).
    """
    model_dir, model_version, metadata = _resolve_model_dir(config, language, task=task)
    model_mode = config.get("model_mode", "hf")

    if model_mode == "heuristics":
        return (None, model_version, {"provider": "heuristics"})

    hf_dir = model_dir / "hf" if (model_dir / "hf").exists() else model_dir

    if not hf_dir.exists():
        return (None, model_version, {})

    config_path = hf_dir / "config.json"
    if not config_path.exists():
        return (None, model_version, {})

    return (hf_dir, model_version, metadata)


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

            # TF-IDF fallback (legacy)
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

            # Heuristics fallback
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
