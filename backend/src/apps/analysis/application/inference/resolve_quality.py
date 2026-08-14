"""
Quality and matching resolution, plus the small helpers that shape their telemetry.
"""
from __future__ import annotations

from django.conf import settings
from typing import Any
from .integrity import ModelAnswerRequired
from .loader import get_matching_bundle, get_quality_bundle
from .tasks.matching import predict_matching_detailed
from .tasks.quality import predict_quality_detailed
from .tasks.quality.loader_bullet_probe import get_bullet_probe_bundle
from .tasks.quality.loader_quality_probe import get_quality_probe_bundle
from .text_probe import probe_metadata_for_task

def _resolve_quality_and_matching(
    *,
    resume_data: dict[str, Any],
    resume_text: str,
    job_text: str,
    lang: str,
    sections: Any,
    config: dict[str, Any],
    final_label: str,
    allow_quality_neural: bool,
    encoder: Any,
    bullet_detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quality_bundle = get_quality_bundle(language=lang, config=config)
    matching_bundle = get_matching_bundle(language=lang, config=config) if job_text else None
    matching_provider = ""
    quality_probe_bundle = get_quality_probe_bundle(config)
    bullet_probe_bundle = get_bullet_probe_bundle(config)

    require_model = bool(config.get("require_model_answer", True))
    quality_score, quality_flags, quality_detail = predict_quality_detailed(
        resume_text,
        lang,
        sections,
        None,
        quality_bundle,
        neural_allowed=allow_quality_neural,
        probe_bundle=quality_probe_bundle,
        embeddings_model=encoder,
        resume_data=resume_data,
        allow_heuristic_answer=not require_model,
        bullet_bundle=bullet_probe_bundle,
        bullet_detail=bullet_detail,
    )
    if quality_score is None:
        raise ModelAnswerRequired(
            "quality",
            str(quality_detail.get("provider") or ""),
            str(quality_detail.get("reason") or ""),
        )
    matching_score = 0
    if job_text:
        matching_score, _, matching_provider = predict_matching_detailed(
            resume_text,
            job_text,
            lang,
            matching_bundle=matching_bundle,
            embeddings_model=encoder,
        )

    quality_extra: dict[str, Any] | None = None
    if quality_detail.get("provider") == "quality_probe" and quality_probe_bundle is not None:
        quality_extra = {
            "labels": [],
            **probe_metadata_for_task(quality_probe_bundle, provider="quality_probe"),
        }

    return {
        "quality_bundle": quality_bundle,
        "matching_bundle": matching_bundle,
        "quality_score": quality_score,
        "quality_flags": quality_flags,
        "quality_detail": quality_detail,
        "quality_extra": quality_extra,
        "matching_score": matching_score,
        "matching_extra": _matching_extra(matching_provider, matching_bundle),
    }


def _dimension_score(
    quality_meta: dict[str, Any],
    key: str,
    fallback: int,
    cap: int,
) -> int:
    """
    A dimension head's answer, capped by the same completeness ceiling as the headline score.

    Falling back to ``fallback`` reproduces the historical behaviour exactly: before the probe, ``ats``
    and ``clarity`` were literal copies of ``quality_score``.
    """
    detail = quality_meta.get("quality_detail")
    dimensions = detail.get("dimensions") if isinstance(detail, dict) else None
    if isinstance(dimensions, dict):
        value = dimensions.get(key)
        if isinstance(value, (int, float)):
            return int(min(int(cap), max(0, round(float(value)))))
    return int(fallback)


def _matching_extra(
    provider: str,
    matching_bundle: tuple[Any, dict] | None,
) -> dict[str, Any] | None:
    """
    Metadata for the step that actually scored the match.

    The bundle's own extra is right only when a bundle answered; when the cascade fell through to
    the sentence embeddings or to keyword overlap, the bundle describes an artifact that did not
    produce the number.
    """
    if provider in ("matching_custom", "matching_hf"):
        if isinstance(matching_bundle, tuple) and isinstance(matching_bundle[1], dict):
            return matching_bundle[1]
        return None
    if provider == "matching_embeddings":
        name = str(getattr(settings, "ANALYSIS_EMBEDDINGS_MODEL_NAME", "") or "MiniLM")
        return {
            "provider": "matching_embeddings",
            "metadata": {
                "model_name_base": name.split("/")[-1][:48],
                "model_version": "matching_embeddings_v1",
                "dataset_version": "",
            },
        }
    if provider == "heuristics":
        return {"provider": "heuristics", "metadata": {}}
    return None
