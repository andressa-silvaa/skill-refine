"""Analysis inference and AI rewrite configuration."""
from __future__ import annotations

from .base import env

ANALYSIS_MODEL_DIR = env.str("ANALYSIS_MODEL_DIR", default="")
ANALYSIS_TFIDF_MODEL_PATH = env.str("ANALYSIS_TFIDF_MODEL_PATH", default="")
ANALYSIS_MODEL_NAME = env.str("ANALYSIS_MODEL_NAME", default="tfidf-logreg-seniority")
ANALYSIS_MODEL_VERSION = env.str("ANALYSIS_MODEL_VERSION", default="analysis_v1")
ANALYSIS_MAX_CHARS_RESUME = env.int("ANALYSIS_MAX_CHARS_RESUME", default=12_000)
ANALYSIS_MAX_CHARS_JOB = env.int("ANALYSIS_MAX_CHARS_JOB", default=8_000)
ANALYSIS_MULTILANG = env.bool("ANALYSIS_MULTILANG", default=False)

AI_REWRITE_CACHE_TTL_SECONDS = env.int("AI_REWRITE_CACHE_TTL_SECONDS", default=600)

AI_CLOUD_BASE_URL = env.str("AI_CLOUD_BASE_URL", default="")
AI_CLOUD_API_KEY = env.str("AI_CLOUD_API_KEY", default="")
AI_CLOUD_MODEL = env.str("AI_CLOUD_MODEL", default="")
AI_CLOUD_TIMEOUT_SECONDS = env.int("AI_CLOUD_TIMEOUT_SECONDS", default=15)

DASHBOARD_SUMMARY_CACHE_TTL_SECONDS = env.int("DASHBOARD_SUMMARY_CACHE_TTL_SECONDS", default=45)
