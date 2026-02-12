"""
Orchestrator: analyze_resume(resume_data, job_description_text, language) -> AnalysisResult.
Coordinates mapper, predictors, postprocess. Applies safety limits.
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from .config import get_config
from .loader import get_model_bundle
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

    # Load model bundle (singleton)
    language_mode = "multi" if config["multilang"] else "mono"
    model_bundle = get_model_bundle(task="seniority", language_mode=language_mode, config=config)

    # Predict seniority
    seniority_class, seniority_provider = predict_seniority(resume_text, lang, model_bundle)
    seniority_score = SENIORITY_TO_SCORE.get(seniority_class, 50)

    # Predict quality
    quality_score, quality_flags = predict_quality(resume_text, lang, sections)

    # Predict matching (optional)
    matching_score = 0
    if job_text:
        matching_score, _ = predict_matching(resume_text, job_text, lang)

    # Model metadata
    if seniority_provider == "heuristics-only":
        model_name = config.get("heuristics_only_model", "heuristics-only")
        model_version = config.get("model_version", "analysis_v1")
    else:
        model_name = config.get("model_name", "tfidf-logreg-seniority")
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
            "provider": "local",
        },
        payload_json={
            "insights": insights,
            "recommendations": recommendations,
            "was_truncated": was_truncated,
        },
    )

    d = result.to_persist_dict()
    return {
        "score": d["score"],
        "task_scores": d["task_scores"],
        "payload_json": d["payload_json"],
        "model_name": d["metadata"]["modelName"],
        "model_version": d["metadata"]["modelVersion"],
        "provider": d["metadata"]["provider"],
    }
