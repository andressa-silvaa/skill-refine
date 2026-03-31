"""
Orchestrator: analyze_resume(resume_data, job_description_text, language) -> AnalysisResult.
Coordinates mapper, predictors, postprocess. Applies safety limits.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.conf import settings

from .config import get_config
from .loader import get_model_bundle, get_quality_bundle, get_matching_bundle
from .postprocess.insights import derive_insights
from .postprocess.recommendations import build_recommendations
from .predictors.matching import predict_matching
from .predictors.quality import predict_quality
from .predictors.seniority import predict_seniority
from .resume_mapper import resume_to_text
from .safety import truncate_text
from .types import AnalysisResult

logger = logging.getLogger(__name__)

SENIORITY_TO_SCORE = {"intern": 25, "junior": 50, "mid": 75, "senior": 100}


def _normalize_provider(provider: str | None) -> str:
    provider = str(provider or "local").strip() or "local"
    return "heuristics" if provider == "heuristics-only" else provider


def _quality_needs_seniority_first(quality_bundle: tuple[Any, dict] | None) -> bool:
    """Hybrid quality uses engineered features that depend on seniority_hint."""
    if not quality_bundle:
        return False
    model_or_none, extra = quality_bundle
    if not isinstance(extra, dict):
        return False
    return extra.get("kind") == "hybrid" and model_or_none is not None


def _task_metadata(
    task: str,
    bundle_extra: dict[str, Any] | None,
    config: dict[str, Any],
) -> dict[str, str]:
    extra = bundle_extra or {}
    metadata = extra.get("metadata") if isinstance(extra.get("metadata"), dict) else {}
    provider = _normalize_provider(extra.get("provider"))
    configured_version = (config.get("model_version_by_task") or {}).get(task) or config.get("model_version", "analysis_v1")
    if provider == "heuristics":
        model_name = config.get("heuristics_only_model", "heuristics-only")
    else:
        model_name = metadata.get("model_name_base") or config.get("model_name", "heuristics-only")
    return {
        "modelName": model_name,
        "modelVersion": metadata.get("model_version") or configured_version,
        "datasetVersion": metadata.get("dataset_version") or "",
        "provider": provider,
    }


def analyze_resume(
    resume_data: dict[str, Any],
    job_description_text: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """
    Full analysis pipeline. Returns dict for ResumeAnalysis persistence.
    - resume_data: resume_detail_payload or { data: { summary, contact, experiences, ... } }
    - job_description_text: optional, for matching
    - language: pt-BR | en-US | es-ES (from user preferences)
    """
    config = get_config(settings)
    lang = (language or "pt-BR").strip()
    max_resume = config["max_chars_resume"]
    max_job = config["max_chars_job"]

    # Map resume to text
    sections = resume_to_text(resume_data, language=lang)
    resume_text = sections.full_text
    resume_text, was_truncated = truncate_text(resume_text, max_resume)
    job_text = ""
    if job_description_text:
        job_text, _ = truncate_text((job_description_text or "").strip(), max_job)

    # Load model bundles (singleton, per language)
    language_mode = "multi" if config["multilang"] else "mono"
    model_bundle = get_model_bundle(task="seniority", language_mode=language_mode, language=lang, config=config)
    quality_bundle = get_quality_bundle(language=lang, config=config)
    matching_bundle = get_matching_bundle(language=lang, config=config) if job_text else None

    parallel_ok = bool(config.get("parallel_inference", True)) and not _quality_needs_seniority_first(
        quality_bundle
    )

    if parallel_ok:
        # HF seniority + HF quality do not depend on each other; optional matching is independent.
        # Overlapping CPU work cuts wall time vs strict sequential forwards on CPU.
        max_workers = 3 if job_text else 2
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            fut_seniority = pool.submit(predict_seniority, resume_text, lang, model_bundle)
            fut_quality = pool.submit(
                predict_quality,
                resume_text,
                lang,
                sections,
                None,
                quality_bundle,
            )
            fut_matching = (
                pool.submit(predict_matching, resume_text, job_text, lang, matching_bundle)
                if job_text
                else None
            )
            seniority_class, seniority_provider = fut_seniority.result()
            quality_score, quality_flags = fut_quality.result()
            matching_score = 0
            if fut_matching is not None:
                matching_score, _ = fut_matching.result()
        seniority_score = SENIORITY_TO_SCORE.get(seniority_class, 50)
    else:
        seniority_class, seniority_provider = predict_seniority(resume_text, lang, model_bundle)
        seniority_score = SENIORITY_TO_SCORE.get(seniority_class, 50)
        quality_score, quality_flags = predict_quality(
            resume_text,
            lang,
            sections,
            seniority_hint=seniority_class,
            quality_bundle=quality_bundle,
        )
        matching_score = 0
        if job_text:
            matching_score, _ = predict_matching(resume_text, job_text, lang, matching_bundle=matching_bundle)

    # Model metadata: prefer from loaded model, else config
    metadata_seniority = model_bundle[1] if isinstance(model_bundle[1], dict) else {}
    metadata_quality = quality_bundle[1] if isinstance(quality_bundle, tuple) and isinstance(quality_bundle[1], dict) else {}
    metadata_matching = (
        matching_bundle[1]
        if isinstance(matching_bundle, tuple) and isinstance(matching_bundle[1], dict)
        else {}
    )
    model_metadata_by_task = {
        "seniority": _task_metadata("seniority", metadata_seniority, config),
        "quality": _task_metadata("quality", metadata_quality, config),
    }
    if job_text:
        model_metadata_by_task["matching"] = _task_metadata("matching", metadata_matching, config)
    model_meta = metadata_seniority.get("metadata") or {}
    provider = metadata_seniority.get("provider") or "local"
    if provider == "heuristics-only" and metadata_quality.get("provider") not in (None, "heuristics-only"):
        model_meta = metadata_quality.get("metadata") or {}
        provider = metadata_quality.get("provider") or "local"
    model_name = model_meta.get("model_name_base") or config.get("model_name", "heuristics-only")
    model_version = model_meta.get("model_version") or config.get("model_version", "analysis_v1")
    dataset_version = model_meta.get("dataset_version") or ""
    if provider == "heuristics-only":
        model_name = config.get("heuristics_only_model", "heuristics-only")
        model_version = config.get("model_version", "analysis_v1")

    # Insights
    insights = derive_insights(seniority_class, quality_flags, sections, resume_text)
    recommendations = build_recommendations(insights, lang)

    # Overall score: weighted average (all scores 0-100)
    if job_text:
        overall = int(0.5 * quality_score + 0.3 * seniority_score + 0.2 * matching_score)
    else:
        overall = int(0.6 * quality_score + 0.4 * seniority_score)
    overall = min(100, max(0, overall))

    result = AnalysisResult(
        score=overall,
        task_scores={
            "ats": quality_score,
            "clarity": quality_score,
            "seniority": seniority_score,
            "matching": matching_score if job_text else None,
        },
        insights=insights,
        recommendations=recommendations,
        metadata={
            "modelName": model_name,
            "modelVersion": model_version,
            "datasetVersion": dataset_version,
            "provider": provider if provider != "heuristics-only" else "heuristics",
        },
        payload_json={
            "insights": insights,
            "recommendations": recommendations,
            "was_truncated": was_truncated,
            "model_metadata_by_task": model_metadata_by_task,
        },
    )

    d = result.to_persist_dict()
    return {
        "score": d["score"],
        "task_scores": d["task_scores"],
        "payload_json": d["payload_json"],
        "model_name": d["metadata"]["modelName"],
        "model_version": d["metadata"]["modelVersion"],
        "dataset_version": d["metadata"].get("datasetVersion", ""),
        "provider": d["metadata"]["provider"],
    }
