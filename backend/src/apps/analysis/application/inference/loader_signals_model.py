"""
Singleton loader for signals-only sklearn seniority (LogReg + scaler [+ calibrator]).

Loads once per process from ``ml/models/<version>/`` (model.joblib + metadata.json).
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from .tasks.seniority.signals_ml_predict import FEATURE_TRANSFORM

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache: dict[str, Any | None] = {}


def _expected_task(meta: dict[str, Any]) -> bool:
    t = str(meta.get("task") or "").strip().lower()
    return t in {"", "seniority_signals", "seniority-signals"}


def _assert_feature_transform(meta: dict[str, Any]) -> None:
    """
    Refuse a bundle fitted on a different feature transform than inference applies.

    Serving a model whose features were built by another formula produces confident nonsense with
    no error anywhere — it is how seniority_signals_v1 came to answer "intern" for every real
    resume. Failing to load instead falls back to the rule policy, which is auditable.
    """
    declared = str(meta.get("feature_transform") or "").strip()
    if declared != FEATURE_TRANSFORM:
        raise ValueError(
            f"feature transform mismatch: bundle={declared or 'none'} inference={FEATURE_TRANSFORM}"
        )


def load_signals_ml_bundle(model_dir: Path) -> dict[str, Any]:
    """Load joblib bundle + metadata (no cache). Raises on invalid artifact."""
    meta_path = model_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"missing metadata.json in {model_dir}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if not _expected_task(meta):
        raise ValueError(f"metadata task incompatible: {meta.get('task')!r}")
    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError("joblib required for signals_ml") from exc
    bundle_path = model_dir / "model.joblib"
    if not bundle_path.exists():
        raise FileNotFoundError(f"missing model.joblib in {model_dir}")
    bundle = joblib.load(bundle_path)
    for key in ("pipeline", "label_encoder", "feature_names"):
        if key not in bundle:
            raise ValueError(f"invalid bundle: missing {key}")
    _assert_feature_transform(meta)
    bundle["_metadata"] = meta
    return bundle


def get_signals_ml_bundle(config: dict[str, Any]) -> dict[str, Any] | None:
    """
    Cached bundle or None when disabled / missing / invalid.

    provider tag: signals_ml
    """
    if not bool(config.get("signals_ml_enabled", False)):
        return None

    key = str(config.get("signals_ml_cache_key", "default"))
    with _lock:
        if key in _cache:
            return _cache[key]

        explicit = str(config.get("signals_ml_model_dir") or "").strip()
        if explicit:
            model_dir = Path(explicit)
        else:
            root = Path(config.get("model_root") or config.get("model_dir") or "")
            sub = str(config.get("signals_ml_model_subdir") or "seniority_signals_v1").strip()
            model_dir = (root / sub) if sub else root
        try:
            bundle = load_signals_ml_bundle(model_dir)
            bundle["_model_dir"] = str(model_dir)
            _cache[key] = bundle
            logger.info("Loaded signals_ml bundle from %s", model_dir)
            return bundle
        except Exception as e:
            logger.warning("signals_ml bundle not loaded: %s", e)
            _cache[key] = None
            return None


def signals_ml_metadata_for_extra(bundle: dict[str, Any] | None) -> dict[str, Any]:
    """Shape compatible with orchestrator / _task_metadata."""
    if not bundle:
        return {}
    meta = bundle.get("_metadata") if isinstance(bundle.get("_metadata"), dict) else {}
    return {
        "model_name_base": meta.get("model_name") or "seniority_signals",
        "model_version": meta.get("model_version") or "",
        "dataset_version": meta.get("dataset_version") or "",
        "task": meta.get("task") or "seniority_signals",
    }


def clear_signals_ml_cache() -> None:
    with _lock:
        _cache.clear()
