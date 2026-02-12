"""
Config for analysis inference: model paths, limits, thresholds.
Read from Django settings / env.
"""
from __future__ import annotations

from pathlib import Path


def _get_repo_root() -> Path:
    """Repo root (parent of backend)."""
    return Path(__file__).resolve().parents[6]


def _default_tfidf_path() -> Path:
    """Default TF-IDF model path (relative to repo)."""
    return _get_repo_root() / "ml" / "models" / "tfidf_seniority" / "tfidf_logreg_seniority.pkl"


def get_config(settings) -> dict:
    """
    Build config dict from Django settings.
    Falls back to defaults when env vars not set.
    """
    repo = _get_repo_root()
    model_dir_raw = getattr(settings, "ANALYSIS_MODEL_DIR", "")
    model_dir = Path(model_dir_raw) if model_dir_raw else repo / "ml" / "models" / "tfidf_seniority"
    tfidf_raw = getattr(settings, "ANALYSIS_TFIDF_MODEL_PATH", "")
    tfidf_path = Path(tfidf_raw) if tfidf_raw else _default_tfidf_path()
    return {
        "model_dir": model_dir,
        "tfidf_model_path": tfidf_path,
        "model_name": getattr(settings, "ANALYSIS_MODEL_NAME", "tfidf-logreg-seniority"),
        "model_version": getattr(settings, "ANALYSIS_MODEL_VERSION", "analysis_v1"),
        "max_chars_resume": int(getattr(settings, "ANALYSIS_MAX_CHARS_RESUME", 12_000)),
        "max_chars_job": int(getattr(settings, "ANALYSIS_MAX_CHARS_JOB", 8_000)),
        "multilang": bool(getattr(settings, "ANALYSIS_MULTILANG", False)),
        "heuristics_only_model": "heuristics-only",
    }
