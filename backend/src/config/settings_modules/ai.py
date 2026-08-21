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

# Target-fit sklearn Ridge (signals + domain one-hot). Artifact: ml/models/target_fit_v1/model.joblib
ANALYSIS_TARGET_FIT_ML_ENABLED = env.bool("ANALYSIS_TARGET_FIT_ML_ENABLED", default=False)
ANALYSIS_TARGET_FIT_MODEL_DIR = env.str("ANALYSIS_TARGET_FIT_MODEL_DIR", default="")
ANALYSIS_TARGET_FIT_ML_SUBDIR = env.str("ANALYSIS_TARGET_FIT_ML_SUBDIR", default="target_fit_v1")

# Linear probe over the frozen multilingual encoder, trained on band_target from text alone.
# Primary seniority decision when it loads; needs ANALYSIS_EMBEDDINGS_ENABLED.
ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED = env.bool("ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED", default=False)
ANALYSIS_TEXT_SENIORITY_PROBE_MODEL_DIR = env.str("ANALYSIS_TEXT_SENIORITY_PROBE_MODEL_DIR", default="")
ANALYSIS_TEXT_SENIORITY_PROBE_SUBDIR = env.str(
    "ANALYSIS_TEXT_SENIORITY_PROBE_SUBDIR", default="text_seniority_probe_v1"
)

# Quality probe over the same encoder: level head on quality_target, plus impact/clarity/ats heads on
# the LLM teacher rubric. Primary decision for the pillar worth 78% of the score.
ANALYSIS_QUALITY_PROBE_ENABLED = env.bool("ANALYSIS_QUALITY_PROBE_ENABLED", default=False)
ANALYSIS_QUALITY_PROBE_MODEL_DIR = env.str("ANALYSIS_QUALITY_PROBE_MODEL_DIR", default="")
ANALYSIS_QUALITY_PROBE_SUBDIR = env.str("ANALYSIS_QUALITY_PROBE_SUBDIR", default="quality_probe_v1")

# Per-bullet attribute probe over the same encoder. Retires METRICS_PATTERN, ACTION_VERBS and
# LEADERSHIP_WORDS, which recover 0.77 / 0.21 / 0.32 of the positives a two-annotator consensus finds;
# LEADERSHIP_WORDS scores below the majority class, so answering "no" to everything beats it.
ANALYSIS_BULLET_PROBE_ENABLED = env.bool("ANALYSIS_BULLET_PROBE_ENABLED", default=False)
ANALYSIS_BULLET_PROBE_MODEL_DIR = env.str("ANALYSIS_BULLET_PROBE_MODEL_DIR", default="")
ANALYSIS_BULLET_PROBE_SUBDIR = env.str("ANALYSIS_BULLET_PROBE_SUBDIR", default="bullet_probe_v1")

# Order the improvement list by measured gain rather than by the order the branches run in. The table
# is correlational (see ml/reports/insight_gain_v3.md) and is used only to sort and to label
# priority, never published as a promised score change.
ANALYSIS_INSIGHT_RANKING_ENABLED = env.bool("ANALYSIS_INSIGHT_RANKING_ENABLED", default=False)
ANALYSIS_INSIGHT_GAIN_MODEL_DIR = env.str("ANALYSIS_INSIGHT_GAIN_MODEL_DIR", default="")
ANALYSIS_INSIGHT_GAIN_SUBDIR = env.str("ANALYSIS_INSIGHT_GAIN_SUBDIR", default="insight_gain_v1")

# Read the resume's language from the document instead of the user's interface preference. The ESCO
# index is per language, so the wrong one costs 29.5 points of occupation retrieval and 14.9 of
# domain (ml/reports/language_mismatch_v3.md). Overrides the preference only above a confidence floor.
ANALYSIS_LANGUAGE_DETECTION_ENABLED = env.bool("ANALYSIS_LANGUAGE_DETECTION_ENABLED", default=False)
ANALYSIS_LANGUAGE_DETECTOR_MODEL_DIR = env.str("ANALYSIS_LANGUAGE_DETECTOR_MODEL_DIR", default="")
ANALYSIS_LANGUAGE_DETECTOR_SUBDIR = env.str(
    "ANALYSIS_LANGUAGE_DETECTOR_SUBDIR", default="language_detector_v1"
)

# Refuse to publish a quality score that came from the regex heuristic instead of the probe.
# `_heuristic_score` averages 41.4 / 52.4 / 57.8 on resumes planted poor / fair / good — nearly flat
# on the axis it claims to measure, while carrying 78% of the final score. A number that uninformative
# is worse than an error, because it is indistinguishable from a model answer on screen.
# Turned off only by the golden snapshot suite, which exists to keep the fallback path correct.
ANALYSIS_REQUIRE_MODEL_ANSWER = env.bool("ANALYSIS_REQUIRE_MODEL_ANSWER", default=True)

# Refuse to start the worker when a probe is enabled but its bundle will not load, instead of logging
# a warning per request and serving regex. Four separate incidents in this project were a missing
# artefact degrading silently (handoff 5.7 and 9.7), so the default is to fail at startup.
ANALYSIS_FAIL_FAST_ON_MISSING_BUNDLE = env.bool("ANALYSIS_FAIL_FAST_ON_MISSING_BUNDLE", default=True)

# Sentence-transformers semantic target fit (multilingual MiniLM by default).
ANALYSIS_EMBEDDINGS_ENABLED = env.bool("ANALYSIS_EMBEDDINGS_ENABLED", default=False)
ANALYSIS_EMBEDDINGS_MODEL_NAME = env.str(
    "ANALYSIS_EMBEDDINGS_MODEL_NAME",
    default="paraphrase-multilingual-MiniLM-L12-v2",
)
# Final target fit = w * embedding + (1-w) * signals (policy / sklearn).
ANALYSIS_TARGET_FIT_EMBED_WEIGHT = env.float("ANALYSIS_TARGET_FIT_EMBED_WEIGHT", default=0.65)

# Zero-shot domain inference by retrieval over the ESCO occupation taxonomy (needs embeddings).
ANALYSIS_ESCO_DOMAIN_ENABLED = env.bool("ANALYSIS_ESCO_DOMAIN_ENABLED", default=True)
ANALYSIS_ESCO_OCCUPATIONS_PATH = env.str("ANALYSIS_ESCO_OCCUPATIONS_PATH", default="")
ANALYSIS_ESCO_EMBEDDINGS_DIR = env.str("ANALYSIS_ESCO_EMBEDDINGS_DIR", default="")
ANALYSIS_ESCO_TOP_K = env.int("ANALYSIS_ESCO_TOP_K", default=5)
# Below this cosine the nearest occupation is noise; the keyword fallback takes over.
ANALYSIS_ESCO_MIN_COSINE = env.float("ANALYSIS_ESCO_MIN_COSINE", default=0.20)
# Preferred labels only: alternative labels measured worse on the v3 corpus.
ANALYSIS_ESCO_MAX_ALT_LABELS = env.int("ANALYSIS_ESCO_MAX_ALT_LABELS", default=0)

# Overall score = quality-only, or blend with seniority / target fit (reduces plateau).
ANALYSIS_OVERALL_BLEND_ENABLED = env.bool("ANALYSIS_OVERALL_BLEND_ENABLED", default=True)
ANALYSIS_OVERALL_WEIGHT_QUALITY = env.float("ANALYSIS_OVERALL_WEIGHT_QUALITY", default=0.78)
ANALYSIS_OVERALL_WEIGHT_SENIORITY = env.float("ANALYSIS_OVERALL_WEIGHT_SENIORITY", default=0.12)
ANALYSIS_OVERALL_WEIGHT_TARGET_FIT = env.float("ANALYSIS_OVERALL_WEIGHT_TARGET_FIT", default=0.10)

AI_REWRITE_CACHE_TTL_SECONDS = env.int("AI_REWRITE_CACHE_TTL_SECONDS", default=600)

AI_CLOUD_BASE_URL = env.str("AI_CLOUD_BASE_URL", default="")
AI_CLOUD_API_KEY = env.str("AI_CLOUD_API_KEY", default="")
AI_CLOUD_MODEL = env.str("AI_CLOUD_MODEL", default="")
AI_CLOUD_TIMEOUT_SECONDS = env.int("AI_CLOUD_TIMEOUT_SECONDS", default=15)

# Optional: LLM-generated natural-language feedback about an already-decided analysis
# result (never decides scores/labels — purely additive, fails safe to None).
ANALYSIS_LLM_FEEDBACK_ENABLED = env.bool("ANALYSIS_LLM_FEEDBACK_ENABLED", default=False)

DASHBOARD_SUMMARY_CACHE_TTL_SECONDS = env.int("DASHBOARD_SUMMARY_CACHE_TTL_SECONDS", default=45)

# Internal review API (GET /analysis/internal/...). Empty = 403 for all.
ANALYSIS_INTERNAL_REVIEW_SECRET = env.str("ANALYSIS_INTERNAL_REVIEW_SECRET", default="")
# When DEBUG is False, secret must be at least this long (production hardening).
ANALYSIS_INTERNAL_SECRET_MIN_LENGTH = env.int("ANALYSIS_INTERNAL_SECRET_MIN_LENGTH", default=20)
# Salt for pseudo-keys (analysisKey, resumeKey, userKey) and dataset keys; falls back to SECRET_KEY prefix.
ANALYSIS_INTERNAL_REVIEW_KEY_SALT = env.str("ANALYSIS_INTERNAL_REVIEW_KEY_SALT", default="")
