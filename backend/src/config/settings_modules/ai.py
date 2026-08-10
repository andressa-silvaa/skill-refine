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

# Signals-only sklearn seniority (LogReg + calibration). Artifact: ml/models/<subdir>/model.joblib
ANALYSIS_SIGNALS_ML_ENABLED = env.bool("ANALYSIS_SIGNALS_ML_ENABLED", default=False)
# Optional absolute path to model dir (overrides ANALYSIS_MODEL_ROOT + ANALYSIS_SIGNALS_ML_SUBDIR)
ANALYSIS_SIGNALS_MODEL_DIR = env.str("ANALYSIS_SIGNALS_MODEL_DIR", default="")
ANALYSIS_SIGNALS_ML_SUBDIR = env.str("ANALYSIS_SIGNALS_ML_SUBDIR", default="seniority_signals_v1")
# If false, thresholds may be read from artifact metadata.json "inference_thresholds" (see export/tuning docs)
ANALYSIS_SIGNALS_THRESHOLDS_FROM_SETTINGS = env.bool("ANALYSIS_SIGNALS_THRESHOLDS_FROM_SETTINGS", default=True)
# Conservative gates for predicted "senior" (documentação TCC / tuning — nomes curtos no .env)
SENIOR_PROB_THRESHOLD = env.float("SENIOR_PROB_THRESHOLD", default=0.70)
SENIOR_MIN_MONTHS = env.int("SENIOR_MIN_MONTHS", default=60)
SENIOR_MIN_EXPERIENCES = env.int("SENIOR_MIN_EXPERIENCES", default=2)
SENIOR_MIN_BULLETS = env.int("SENIOR_MIN_BULLETS", default=6)
ANALYSIS_SIGNALS_ML_SENIOR_PROB_THRESHOLD = env.float(
    "ANALYSIS_SIGNALS_ML_SENIOR_PROB_THRESHOLD", default=SENIOR_PROB_THRESHOLD
)
ANALYSIS_SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS = env.int(
    "ANALYSIS_SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS", default=SENIOR_MIN_MONTHS
)
ANALYSIS_SIGNALS_ML_SENIOR_MIN_EXPERIENCES = env.int(
    "ANALYSIS_SIGNALS_ML_SENIOR_MIN_EXPERIENCES", default=SENIOR_MIN_EXPERIENCES
)
ANALYSIS_SIGNALS_ML_SENIOR_MIN_BULLETS = env.int(
    "ANALYSIS_SIGNALS_ML_SENIOR_MIN_BULLETS", default=SENIOR_MIN_BULLETS
)
# Minimum text/completeness to trust signals_ml (aligned with neural gating by default)
ANALYSIS_SIGNALS_ML_MIN_COMPLETENESS = env.int("ANALYSIS_SIGNALS_ML_MIN_COMPLETENESS", default=52)
ANALYSIS_SIGNALS_ML_MIN_WORDS = env.int("ANALYSIS_SIGNALS_ML_MIN_WORDS", default=48)

# Target-fit sklearn Ridge (signals + domain one-hot). Artifact: ml/models/target_fit_v1/model.joblib
ANALYSIS_TARGET_FIT_ML_ENABLED = env.bool("ANALYSIS_TARGET_FIT_ML_ENABLED", default=False)
ANALYSIS_TARGET_FIT_MODEL_DIR = env.str("ANALYSIS_TARGET_FIT_MODEL_DIR", default="")
ANALYSIS_TARGET_FIT_ML_SUBDIR = env.str("ANALYSIS_TARGET_FIT_ML_SUBDIR", default="target_fit_v1")

# BERT / XLM-R text seniority (HF sequence classification export under ml/models/text_seniority_v1/)
ANALYSIS_TEXT_SENIORITY_ENABLED = env.bool("ANALYSIS_TEXT_SENIORITY_ENABLED", default=False)
ANALYSIS_TEXT_SENIORITY_MODEL_DIR = env.str("ANALYSIS_TEXT_SENIORITY_MODEL_DIR", default="")
# Optional Hugging Face hub id when MODEL_DIR is empty (slow first run; prefer local export).
ANALYSIS_TEXT_SENIORITY_HUB_ID = env.str("ANALYSIS_TEXT_SENIORITY_HUB_ID", default="")
# Fuse structured signals with text (neural if loaded, else lexical evidence). Safe on CPU.
ANALYSIS_TEXT_SENIORITY_FUSION_ENABLED = env.bool("ANALYSIS_TEXT_SENIORITY_FUSION_ENABLED", default=True)

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
