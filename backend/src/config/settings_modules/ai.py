"""Analysis inference and AI rewrite configuration."""
from __future__ import annotations

from .base import env

# Legacy (TF-IDF)
ANALYSIS_MODEL_DIR = env.str("ANALYSIS_MODEL_DIR", default="")
ANALYSIS_TFIDF_MODEL_PATH = env.str("ANALYSIS_TFIDF_MODEL_PATH", default="")
ANALYSIS_MODEL_NAME = env.str("ANALYSIS_MODEL_NAME", default="tfidf-logreg-seniority")

# Model root and versioning (ml/models/)
ANALYSIS_MODEL_ROOT = env.str("ANALYSIS_MODEL_ROOT", default="")
ANALYSIS_MODEL_VERSION = env.str("ANALYSIS_MODEL_VERSION", default="analysis_v1_pt")
ANALYSIS_MODEL_MODE = env.str("ANALYSIS_MODEL_MODE", default="hf")  # hf | onnx | heuristics
ANALYSIS_ALLOW_HEURISTICS_FALLBACK = env.bool("ANALYSIS_ALLOW_HEURISTICS_FALLBACK", default=True)
ANALYSIS_MULTILANG = env.bool("ANALYSIS_MULTILANG", default=False)
ANALYSIS_MODEL_VERSION_BY_LANG = env.str("ANALYSIS_MODEL_VERSION_BY_LANG", default="")  # pt-BR=analysis_v1_pt;en-US=analysis_v1_multi
ANALYSIS_MODEL_VERSION_BY_TASK = env.str("ANALYSIS_MODEL_VERSION_BY_TASK", default="")  # seniority=analysis_v1_pt;quality=analysis_quality_v1_pt
ANALYSIS_MODEL_VERSION_BY_TASK_LANG = env.str("ANALYSIS_MODEL_VERSION_BY_TASK_LANG", default="")  # quality:pt-BR=analysis_quality_v9_pt
ANALYSIS_PREWARM_ENABLED = env.bool("ANALYSIS_PREWARM_ENABLED", default=False)
ANALYSIS_PREWARM_LANGUAGES = env.str("ANALYSIS_PREWARM_LANGUAGES", default="pt-BR")
# Run seniority/quality/matching HF passes concurrently when safe (not hybrid quality).
ANALYSIS_PARALLEL_INFERENCE = env.bool("ANALYSIS_PARALLEL_INFERENCE", default=True)

ANALYSIS_MAX_CHARS_RESUME = env.int("ANALYSIS_MAX_CHARS_RESUME", default=12_000)
ANALYSIS_MAX_CHARS_JOB = env.int("ANALYSIS_MAX_CHARS_JOB", default=8_000)

AI_REWRITE_CACHE_TTL_SECONDS = env.int("AI_REWRITE_CACHE_TTL_SECONDS", default=600)

AI_CLOUD_BASE_URL = env.str("AI_CLOUD_BASE_URL", default="")
AI_CLOUD_API_KEY = env.str("AI_CLOUD_API_KEY", default="")
AI_CLOUD_MODEL = env.str("AI_CLOUD_MODEL", default="")
AI_CLOUD_TIMEOUT_SECONDS = env.int("AI_CLOUD_TIMEOUT_SECONDS", default=15)

DASHBOARD_SUMMARY_CACHE_TTL_SECONDS = env.int("DASHBOARD_SUMMARY_CACHE_TTL_SECONDS", default=45)
