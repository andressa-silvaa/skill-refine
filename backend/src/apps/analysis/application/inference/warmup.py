from __future__ import annotations

import logging
import time

from django.conf import settings

from .config import get_config
from .loader import get_matching_bundle, get_model_bundle, get_quality_bundle
from .tasks.target_fit.esco_retrieval import warm_occupation_index
from .tasks.target_fit.loader_embeddings import get_embeddings_model

logger = logging.getLogger(__name__)


def _parse_languages(raw: str) -> list[str]:
    tokens = str(raw or "").replace(";", ",").split(",")
    languages = [token.strip() for token in tokens if token.strip()]
    return languages or ["pt-BR"]


def prewarm_analysis_models() -> None:
    """
    Load configured analysis bundles once at Celery startup.

    We intentionally keep the default language list small so local startup cost
    remains bounded while the user-facing first analysis stays fast.
    """
    config = get_config(settings)
    languages = _parse_languages(getattr(settings, "ANALYSIS_PREWARM_LANGUAGES", "pt-BR"))
    language_mode = "multi" if config.get("multilang") else "mono"

    started_at = time.monotonic()
    loaded: list[str] = []

    esco_model = None
    if config.get("embeddings_enabled") and config.get("esco_domain_enabled"):
        esco_model = get_embeddings_model(settings)

    for language in languages:
        lang_started_at = time.monotonic()
        get_model_bundle(task="seniority", language_mode=language_mode, language=language, config=config)
        get_quality_bundle(language=language, config=config)
        get_matching_bundle(language=language, config=config)
        if esco_model is not None:
            warm_occupation_index(esco_model, language, config.get("esco_options"))
        loaded.append(f"{language}:{int((time.monotonic() - lang_started_at) * 1000)}ms")

    logger.info(
        "Analysis models pre-warmed",
        extra={
            "languages": languages,
            "durations": loaded,
            "elapsed_ms": int((time.monotonic() - started_at) * 1000),
        },
    )
