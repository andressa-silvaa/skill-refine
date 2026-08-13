from __future__ import annotations

import logging
import time
from typing import Any

from django.conf import settings

from .config import get_config
from .loader import get_matching_bundle, get_model_bundle, get_quality_bundle
from .tasks.quality.loader_bullet_probe import get_bullet_probe_bundle
from .tasks.quality.loader_quality_probe import get_quality_probe_bundle
from .tasks.seniority.text.loader_seniority_probe import get_seniority_probe_bundle
from .tasks.target_fit.esco_retrieval import warm_occupation_index
from .tasks.target_fit.loader_embeddings import get_embeddings_model

logger = logging.getLogger(__name__)


class ProbeBundleMissing(RuntimeError):
    """A probe is enabled by configuration but its bundle will not load."""


def verify_enabled_probes(config: dict[str, Any]) -> list[str]:
    """
    Check every enabled probe actually loads, and return the problems found.

    Four separate incidents in this project were a missing artefact degrading in silence: the ESCO
    taxonomy excluded by .gitignore dropped domain inference to a 21% keyword matcher, `ml/models/`
    was excluded the same way, `ANALYSIS_EMBEDDINGS_ENABLED` lived only in an untracked .env, and a
    test stub of the wrong width made the probes skip while the assertion still passed. In every case
    the code logged a warning per request and carried on answering with regex.

    So the check runs once, at startup, where a failure is visible and attributable — not per request,
    where it is a warning nobody reads.
    """
    problems: list[str] = []

    encoder_needed = (
        config.get("quality_probe_enabled")
        or config.get("text_seniority_probe_enabled")
        or config.get("bullet_probe_enabled")
    )
    if encoder_needed and not config.get("embeddings_enabled"):
        problems.append(
            "a probe is enabled but ANALYSIS_EMBEDDINGS_ENABLED is off; both probes read that encoder"
        )
    if encoder_needed and config.get("embeddings_enabled") and get_embeddings_model(settings) is None:
        problems.append(
            "ANALYSIS_EMBEDDINGS_ENABLED is on but the sentence-transformers encoder did not load"
        )

    if config.get("quality_probe_enabled") and get_quality_probe_bundle(config) is None:
        problems.append(
            "ANALYSIS_QUALITY_PROBE_ENABLED is on but the quality_probe bundle did not load from "
            f"{config.get('model_root')}"
        )
    if config.get("text_seniority_probe_enabled") and get_seniority_probe_bundle(config) is None:
        problems.append(
            "ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED is on but the text_seniority_probe bundle did not "
            f"load from {config.get('model_root')}"
        )
    if config.get("bullet_probe_enabled") and get_bullet_probe_bundle(config) is None:
        problems.append(
            "ANALYSIS_BULLET_PROBE_ENABLED is on but the bullet_probe bundle did not load from "
            f"{config.get('model_root')}"
        )
    return problems


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

    problems = verify_enabled_probes(config)
    if problems:
        summary = "; ".join(problems)
        if config.get("fail_fast_on_missing_bundle", True):
            logger.error("Analysis probes unavailable, refusing to start: %s", summary)
            raise ProbeBundleMissing(
                f"{summary}. Set ANALYSIS_FAIL_FAST_ON_MISSING_BUNDLE=false to start anyway, which "
                "makes quality refuse every analysis and seniority answer with the rule."
            )
        logger.warning("Analysis probes unavailable, continuing degraded: %s", summary)

    logger.info(
        "Analysis models pre-warmed",
        extra={
            "languages": languages,
            "durations": loaded,
            "probes_ok": not problems,
            "elapsed_ms": int((time.monotonic() - started_at) * 1000),
        },
    )
