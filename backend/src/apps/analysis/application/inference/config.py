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
    }
