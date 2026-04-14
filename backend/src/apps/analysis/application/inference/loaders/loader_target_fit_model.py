"""
Singleton loader for target-fit sklearn Ridge bundle (model.joblib + metadata.json).

provider tag: target_fit_ml
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache: dict[str, Any | None] = {}


def _expected_task(meta: dict[str, Any]) -> bool:
    t = str(meta.get("task") or "").strip().lower()
    return t in {"target_fit_signals", "target-fit-signals", "target_fit"}


def load_target_fit_ml_bundle(model_dir: Path) -> dict[str, Any]:
    meta_path = model_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"missing metadata.json in {model_dir}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if not _expected_task(meta):
        raise ValueError(f"metadata task incompatible: {meta.get('task')!r}")
    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError("joblib required for target_fit_ml") from exc
    bundle_path = model_dir / "model.joblib"
    if not bundle_path.exists():
        raise FileNotFoundError(f"missing model.joblib in {model_dir}")
    bundle = joblib.load(bundle_path)
    for key in ("model", "scaler", "feature_names"):
        if key not in bundle:
            raise ValueError(f"invalid bundle: missing {key}")
    bundle["_metadata"] = meta
    return bundle


def get_target_fit_ml_bundle(config: dict[str, Any]) -> dict[str, Any] | None:
    if not bool(config.get("target_fit_ml_enabled", False)):
        return None

    key = str(config.get("target_fit_ml_cache_key", "target_fit_v1"))
    with _lock:
        if key in _cache:
            return _cache[key]

        explicit = str(config.get("target_fit_ml_model_dir") or "").strip()
        if explicit:
            model_dir = Path(explicit)
        else:
            root = Path(config.get("model_root") or config.get("model_dir") or "")
            sub = str(config.get("target_fit_ml_model_subdir") or "target_fit_v1").strip()
            model_dir = (root / sub) if sub else root
        try:
            bundle = load_target_fit_ml_bundle(model_dir)
            bundle["_model_dir"] = str(model_dir)
            _cache[key] = bundle
            logger.info("Loaded target_fit_ml bundle from %s", model_dir)
            return bundle
        except Exception as e:
            logger.warning("target_fit_ml bundle not loaded: %s", e)
            _cache[key] = None
            return None


def predict_target_fit_ml_score(
    bundle: dict[str, Any],
    *,
    signals: Any,
    resume_domain: str,
    target_domain: str,
    has_job_text: bool,
) -> int:
    import numpy as np

    from apps.analysis.application.inference.target_fit.ml_feature_row import target_fit_feature_row

    model = bundle["model"]
    scaler = bundle["scaler"]
    names = bundle.get("feature_names") or []
    row = target_fit_feature_row(
        signals,
        resume_domain=resume_domain,
        target_domain=target_domain,
        has_job_text=has_job_text,
    )
    if names and len(row) != len(names):
        raise ValueError(f"feature length mismatch: got {len(row)} expected {len(names)}")
    x = np.asarray([row], dtype=np.float64)
    pred = float(model.predict(scaler.transform(x))[0])
    return int(max(0, min(100, round(pred))))


def target_fit_ml_metadata_for_task(bundle: dict[str, Any] | None) -> dict[str, Any]:
    if not bundle:
        return {}
    meta = bundle.get("_metadata") if isinstance(bundle.get("_metadata"), dict) else {}
    return {
        "model_name_base": meta.get("model_name") or "target_fit_signals",
        "model_version": meta.get("model_version") or "",
        "dataset_version": meta.get("dataset_version") or "",
        "task": meta.get("task") or "target_fit_signals",
    }


def clear_target_fit_ml_cache() -> None:
    with _lock:
        _cache.clear()
