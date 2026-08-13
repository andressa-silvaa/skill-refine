"""
Singleton loader for the text-seniority probe bundle (model.joblib + metadata.json).

provider tag: text_seniority_probe
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from apps.analysis.application.inference.text_probe import load_probe_bundle

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache: dict[str, dict[str, Any] | None] = {}

TASK = "text_seniority_probe"


def get_seniority_probe_bundle(config: dict[str, Any]) -> dict[str, Any] | None:
    if not bool(config.get("text_seniority_probe_enabled", False)):
        return None

    key = str(config.get("text_seniority_probe_cache_key") or "text_seniority_probe_v1")
    with _lock:
        if key in _cache:
            return _cache[key]

        explicit = str(config.get("text_seniority_probe_model_dir") or "").strip()
        if explicit:
            model_dir = Path(explicit)
        else:
            root = Path(config.get("model_root") or config.get("model_dir") or "")
            subdir = str(config.get("text_seniority_probe_subdir") or "text_seniority_probe_v1")
            model_dir = root / subdir
        try:
            bundle = load_probe_bundle(model_dir, expected_task=TASK)
            _cache[key] = bundle
            logger.info("Loaded text_seniority_probe bundle from %s", model_dir)
            return bundle
        except Exception as exc:
            logger.warning("text_seniority_probe bundle not loaded: %s", exc)
            _cache[key] = None
            return None


def clear_seniority_probe_cache() -> None:
    with _lock:
        _cache.clear()
