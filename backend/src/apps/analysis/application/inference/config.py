"""
Config for analysis inference: model paths, limits, thresholds.
Read from Django settings / env.
"""
from __future__ import annotations

from pathlib import Path


def _get_repo_root() -> Path:
    """Repo root (parent of backend)."""
    return Path(__file__).resolve().parents[6]


def _default_model_root() -> Path:
    """Default model root: ml/models (relative to repo)."""
    return _get_repo_root() / "ml" / "models"


def _default_tfidf_path() -> Path:
    """Default TF-IDF model path (relative to repo)."""
    return _get_repo_root() / "ml" / "models" / "tfidf_seniority" / "tfidf_logreg_seniority.pkl"


def _parse_model_version_by_lang(raw: str) -> dict[str, str]:
    """Parse ANALYSIS_MODEL_VERSION_BY_LANG: pt-BR=analysis_v1_pt;en-US=analysis_v1_multi"""
    out = {}
    if not raw or not raw.strip():
        return out
    for part in raw.strip().split(";"):
        part = part.strip()
        if "=" in part:
            lang, ver = part.split("=", 1)
            out[lang.strip()] = ver.strip()
    return out


def _parse_model_version_by_task(raw: str) -> dict[str, str]:
    """Parse ANALYSIS_MODEL_VERSION_BY_TASK: seniority=analysis_v1_pt;quality=analysis_quality_v1_pt"""
    out = {}
    if not raw or not raw.strip():
        return out
    for part in raw.strip().split(";"):
        part = part.strip()
        if "=" in part:
            task, ver = part.split("=", 1)
            out[task.strip()] = ver.strip()
    return out


def _parse_model_version_by_task_lang(raw: str) -> dict[str, str]:
    """Parse ANALYSIS_MODEL_VERSION_BY_TASK_LANG: quality:pt-BR=analysis_quality_v9_pt"""
    out = {}
    if not raw or not raw.strip():
        return out
    for part in raw.strip().split(";"):
        part = part.strip()
        if "=" in part:
            task_lang, ver = part.split("=", 1)
            out[task_lang.strip()] = ver.strip()
    return out


def _esco_options(settings) -> dict:
    """Kwargs for esco_retrieval; omitted keys keep the module defaults."""
    options: dict = {
        "top_k": int(getattr(settings, "ANALYSIS_ESCO_TOP_K", 5)),
        "min_cosine": float(getattr(settings, "ANALYSIS_ESCO_MIN_COSINE", 0.20)),
        "max_alt_labels": int(getattr(settings, "ANALYSIS_ESCO_MAX_ALT_LABELS", 0)),
        "model_name": str(getattr(settings, "ANALYSIS_EMBEDDINGS_MODEL_NAME", "") or ""),
    }
    occupations_path = str(getattr(settings, "ANALYSIS_ESCO_OCCUPATIONS_PATH", "") or "").strip()
    if occupations_path:
        options["occupations_path"] = occupations_path
    cache_dir = str(getattr(settings, "ANALYSIS_ESCO_EMBEDDINGS_DIR", "") or "").strip()
    if cache_dir:
        options["cache_dir"] = cache_dir
    return options


def get_config(settings) -> dict:
    """
    Build config dict from Django settings.
    Falls back to defaults when env vars not set.
    """
    repo = _get_repo_root()
    model_root_raw = getattr(settings, "ANALYSIS_MODEL_ROOT", "")
    model_root = Path(model_root_raw) if model_root_raw else _default_model_root()
    tfidf_raw = getattr(settings, "ANALYSIS_TFIDF_MODEL_PATH", "")
    tfidf_path = Path(tfidf_raw) if tfidf_raw else _default_tfidf_path()
    model_version_by_lang = _parse_model_version_by_lang(
        getattr(settings, "ANALYSIS_MODEL_VERSION_BY_LANG", "") or ""
    )
    model_version_by_task = _parse_model_version_by_task(
        getattr(settings, "ANALYSIS_MODEL_VERSION_BY_TASK", "") or ""
    )
    model_version_by_task_lang = _parse_model_version_by_task_lang(
        getattr(settings, "ANALYSIS_MODEL_VERSION_BY_TASK_LANG", "") or ""
    )
    return {
        "model_dir": getattr(settings, "ANALYSIS_MODEL_DIR", "") or model_root,
        "model_root": model_root,
        "tfidf_model_path": tfidf_path,
        "model_name": getattr(settings, "ANALYSIS_MODEL_NAME", "tfidf-logreg-seniority"),
        "model_version": getattr(settings, "ANALYSIS_MODEL_VERSION", "analysis_v1_pt"),
        "model_mode": getattr(settings, "ANALYSIS_MODEL_MODE", "hf"),
        "allow_heuristics_fallback": bool(getattr(settings, "ANALYSIS_ALLOW_HEURISTICS_FALLBACK", True)),
        "model_version_by_lang": model_version_by_lang,
        "model_version_by_task": model_version_by_task,
        "model_version_by_task_lang": model_version_by_task_lang,
        "max_chars_resume": int(getattr(settings, "ANALYSIS_MAX_CHARS_RESUME", 12_000)),
        "max_chars_job": int(getattr(settings, "ANALYSIS_MAX_CHARS_JOB", 8_000)),
        "multilang": bool(getattr(settings, "ANALYSIS_MULTILANG", False)),
        "parallel_inference": bool(getattr(settings, "ANALYSIS_PARALLEL_INFERENCE", True)),
        "heuristics_only_model": "heuristics-only",
        "target_fit_ml_enabled": bool(getattr(settings, "ANALYSIS_TARGET_FIT_ML_ENABLED", False)),
        "target_fit_ml_model_dir": str(getattr(settings, "ANALYSIS_TARGET_FIT_MODEL_DIR", "") or "").strip(),
        "target_fit_ml_model_subdir": str(
            getattr(settings, "ANALYSIS_TARGET_FIT_ML_SUBDIR", "target_fit_v1") or "target_fit_v1"
        ),
        "target_fit_ml_cache_key": "target_fit_v1",
        "text_seniority_probe_enabled": bool(
            getattr(settings, "ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED", False)
        ),
        "text_seniority_probe_model_dir": str(
            getattr(settings, "ANALYSIS_TEXT_SENIORITY_PROBE_MODEL_DIR", "") or ""
        ).strip(),
        "text_seniority_probe_subdir": str(
            getattr(settings, "ANALYSIS_TEXT_SENIORITY_PROBE_SUBDIR", "text_seniority_probe_v1")
            or "text_seniority_probe_v1"
        ),
        "text_seniority_probe_cache_key": "text_seniority_probe_v1",
        "quality_probe_enabled": bool(getattr(settings, "ANALYSIS_QUALITY_PROBE_ENABLED", False)),
        "quality_probe_model_dir": str(
            getattr(settings, "ANALYSIS_QUALITY_PROBE_MODEL_DIR", "") or ""
        ).strip(),
        "quality_probe_subdir": str(
            getattr(settings, "ANALYSIS_QUALITY_PROBE_SUBDIR", "quality_probe_v1") or "quality_probe_v1"
        ),
        "quality_probe_cache_key": "quality_probe_v1",
        "bullet_probe_enabled": bool(getattr(settings, "ANALYSIS_BULLET_PROBE_ENABLED", False)),
        "bullet_probe_model_dir": str(
            getattr(settings, "ANALYSIS_BULLET_PROBE_MODEL_DIR", "") or ""
        ).strip(),
        "bullet_probe_subdir": str(
            getattr(settings, "ANALYSIS_BULLET_PROBE_SUBDIR", "bullet_probe_v1") or "bullet_probe_v1"
        ),
        "bullet_probe_cache_key": "bullet_probe_v1",
        "insight_ranking_enabled": bool(
            getattr(settings, "ANALYSIS_INSIGHT_RANKING_ENABLED", False)
        ),
        "insight_gain_model_dir": str(
            getattr(settings, "ANALYSIS_INSIGHT_GAIN_MODEL_DIR", "") or ""
        ).strip(),
        "insight_gain_subdir": str(
            getattr(settings, "ANALYSIS_INSIGHT_GAIN_SUBDIR", "insight_gain_v1")
            or "insight_gain_v1"
        ),
        "insight_gain_cache_key": "insight_gain_v1",
        "language_detection_enabled": bool(
            getattr(settings, "ANALYSIS_LANGUAGE_DETECTION_ENABLED", False)
        ),
        "language_detector_model_dir": str(
            getattr(settings, "ANALYSIS_LANGUAGE_DETECTOR_MODEL_DIR", "") or ""
        ).strip(),
        "language_detector_subdir": str(
            getattr(settings, "ANALYSIS_LANGUAGE_DETECTOR_SUBDIR", "language_detector_v1")
            or "language_detector_v1"
        ),
        "language_detector_cache_key": "language_detector_v1",
        "require_model_answer": bool(getattr(settings, "ANALYSIS_REQUIRE_MODEL_ANSWER", True)),
        "fail_fast_on_missing_bundle": bool(
            getattr(settings, "ANALYSIS_FAIL_FAST_ON_MISSING_BUNDLE", True)
        ),
        "embeddings_enabled": bool(getattr(settings, "ANALYSIS_EMBEDDINGS_ENABLED", False)),
        "target_fit_embed_weight": float(getattr(settings, "ANALYSIS_TARGET_FIT_EMBED_WEIGHT", 0.65)),
        "esco_domain_enabled": bool(getattr(settings, "ANALYSIS_ESCO_DOMAIN_ENABLED", True)),
        "esco_options": _esco_options(settings),
        "overall_blend_enabled": bool(getattr(settings, "ANALYSIS_OVERALL_BLEND_ENABLED", True)),
        "overall_w_quality": float(getattr(settings, "ANALYSIS_OVERALL_WEIGHT_QUALITY", 0.78)),
        "overall_w_seniority": float(getattr(settings, "ANALYSIS_OVERALL_WEIGHT_SENIORITY", 0.12)),
        "overall_w_target_fit": float(getattr(settings, "ANALYSIS_OVERALL_WEIGHT_TARGET_FIT", 0.10)),
    }
