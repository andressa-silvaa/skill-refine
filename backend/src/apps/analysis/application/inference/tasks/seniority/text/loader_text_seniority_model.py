"""
Singleton loader for HF sequence-classification seniority model (local export).
Falls back to None if disabled, missing deps, or load error (CPU-safe; Windows may need WSL for some builds).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_bundle: dict[str, Any] | None = None
_bundle_key: str = ""
_transformers_unavailable: bool = False


def _enabled(settings) -> bool:
    return bool(getattr(settings, "ANALYSIS_TEXT_SENIORITY_ENABLED", False))


def get_text_seniority_bundle(settings) -> dict[str, Any] | None:
    """
    Returns {"model", "tokenizer", "metadata"} or None.
    Loads once per process.
    """
    global _bundle, _bundle_key, _transformers_unavailable
    if not _enabled(settings):
        return None
    if _transformers_unavailable:
        return None
    raw_dir = str(getattr(settings, "ANALYSIS_TEXT_SENIORITY_MODEL_DIR", "") or "").strip()
    hub = str(getattr(settings, "ANALYSIS_TEXT_SENIORITY_HUB_ID", "") or "").strip()
    key = f"{raw_dir}|{hub}"
    if _bundle is not None and _bundle_key == key:
        return _bundle

    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except Exception as exc:
        _transformers_unavailable = True
        logger.warning(
            "text_seniority: transformers/torch unavailable (%s). "
            "Fix PyTorch (reinstall CPU wheel) or use WSL2; disabling neural text seniority for this process.",
            exc,
        )
        _bundle, _bundle_key = None, key
        return None

    load_path = raw_dir
    if not load_path and hub:
        load_path = hub
    if not load_path:
        logger.info("text_seniority: ANALYSIS_TEXT_SENIORITY_MODEL_DIR / HUB_ID empty; neural path off")
        _bundle, _bundle_key = None, key
        return None

    try:
        path = Path(load_path)
        if path.exists() and path.is_dir():
            tok = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(str(path), local_files_only=True)
        else:
            tok = AutoTokenizer.from_pretrained(load_path)
            model = AutoModelForSequenceClassification.from_pretrained(load_path)
        model.eval()
        meta: dict[str, Any] = {
            "model_name_base": str(load_path).split("/")[-1][:64],
            "model_version": "text_seniority_bundle",
            "dataset_version": "",
            "provider": "hf_local" if path.exists() and path.is_dir() else "hf_hub",
        }
        meta_path = path / "metadata.json" if path.exists() and path.is_dir() else None
        if meta_path and meta_path.is_file():
            try:
                with open(meta_path, encoding="utf-8") as f:
                    file_meta = json.load(f)
                if isinstance(file_meta, dict):
                    meta = {**meta, **file_meta}
            except Exception as exc:
                logger.warning("text_seniority: could not read metadata.json (%s)", exc)
        _bundle = {"model": model, "tokenizer": tok, "metadata": meta}
        _bundle_key = key
        logger.info("text_seniority: loaded from %s", load_path)
        return _bundle
    except Exception as exc:
        logger.warning("text_seniority: failed to load (%s). Use WSL/Linux or check ANALYSIS_TEXT_SENIORITY_MODEL_DIR.", exc)
        _bundle, _bundle_key = None, key
        return None


def clear_text_seniority_cache() -> None:
    global _bundle, _bundle_key, _transformers_unavailable
    _bundle = None
    _bundle_key = ""
    _transformers_unavailable = False
