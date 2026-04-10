"""
Orchestrator: analyze_resume(resume_data, job_description_text, language) -> AnalysisResult.
Quality (currículo) is separate from senioridade (estimativa). Score principal = qualidade.
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from .completeness import assess_completeness, matching_score_cap, quality_score_cap
from .config import get_config, get_signals_ml_thresholds
from .loader import get_model_bundle, get_quality_bundle, get_matching_bundle
from .loader_signals_model import get_signals_ml_bundle, signals_ml_metadata_for_extra
from .postprocess.insights import derive_insights
from .postprocess.recommendations import build_recommendations
from .predictors.matching import predict_matching
from .predictors.quality import predict_quality
from .resume_mapper import resume_to_text
from .resume_signals import is_thin_student_or_intern_profile
from .safety import truncate_text
from .predictors.seniority import SENIORITY_LABELS
from .seniority.ml_adjust import ml_adjust_seniority
from .seniority.rule_based import clamp_seniority_vetoes, rule_based_seniority
from .seniority.signals_ml_predict import signals_ml_predict
from .signals import extract_resume_signals
from .types import AnalysisResult

logger = logging.getLogger(__name__)

SENIORITY_TO_SCORE = {"intern": 25, "junior": 50, "mid": 75, "senior": 100}


def _normalize_provider(provider: str | None) -> str:
    provider = str(provider or "local").strip() or "local"
    return "heuristics" if provider == "heuristics-only" else provider


def _quality_needs_seniority_first(quality_bundle: tuple[Any, dict] | None) -> bool:
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
    """
    config = get_config(settings)
    lang = (language or "pt-BR").strip()
    max_resume = config["max_chars_resume"]
    max_job = config["max_chars_job"]

    sections = resume_to_text(resume_data, language=lang)
    resume_text = sections.full_text
    resume_text, was_truncated = truncate_text(resume_text, max_resume)

    rs = extract_resume_signals(resume_data, sections, language=lang)
    completeness = {"score": rs.completeness_score, "level": rs.completeness_level}
    level = rs.completeness_level

    allow_quality_neural = level != "insufficient"
    allow_ml_seniority = level == "adequate"

    base_label, base_confidence, base_evidence = rule_based_seniority(rs)

    language_mode = "multi" if config["multilang"] else "mono"
    signals_bundle = get_signals_ml_bundle(config)
    final_label = base_label
    seniority_confidence = base_confidence
    seniority_evidence = list(base_evidence)
    ml_status = "skipped_no_model"
    seniority_from_signals_path = False

    if signals_bundle:
        sm_cfg = get_signals_ml_thresholds(settings)
        ml_lab, ml_conf, _probs, ml_ev, st = signals_ml_predict(signals_bundle, rs, sm_cfg)
        if st == "applied":
            merged_evidence = list(base_evidence) + list(ml_ev)
            fl, veto_ev = clamp_seniority_vetoes(ml_lab, rs)
            merged_evidence.extend(veto_ev)
            final_label = fl
            seniority_confidence = ml_conf
            seniority_evidence = merged_evidence
            ml_status = "applied_signals_ml"
            seniority_from_signals_path = True
        elif st == "error":
            signals_bundle = None
        else:
            seniority_evidence = list(base_evidence) + list(ml_ev)
            ml_status = f"skipped_signals_ml:{st}"
            seniority_from_signals_path = True

    if seniority_from_signals_path and signals_bundle is not None:
        meta_d = signals_ml_metadata_for_extra(signals_bundle)
        model_bundle = (
            None,
            {
                "labels": list(SENIORITY_LABELS),
                "metadata": meta_d,
                "provider": "signals_ml",
            },
        )
    else:
        model_bundle = get_model_bundle(task="seniority", language_mode=language_mode, language=lang, config=config)
        final_label, seniority_confidence, seniority_evidence, ml_status = ml_adjust_seniority(
            resume_text,
            lang,
            base_label,
            base_confidence,
            base_evidence,
            rs,
            model_bundle,
            allow_ml=allow_ml_seniority,
        )
    seniority_score = SENIORITY_TO_SCORE.get(final_label, 50)

    job_text = ""
    if job_description_text:
        job_text, _ = truncate_text((job_description_text or "").strip(), max_job)

    quality_bundle = get_quality_bundle(language=lang, config=config)
    matching_bundle = get_matching_bundle(language=lang, config=config) if job_text else None

    if _quality_needs_seniority_first(quality_bundle):
        quality_score, quality_flags = predict_quality(
            resume_text,
            lang,
            sections,
            seniority_hint=final_label,
            quality_bundle=quality_bundle,
            neural_allowed=allow_quality_neural,
        )
        matching_score = 0
        if job_text:
            matching_score, _ = predict_matching(resume_text, job_text, lang, matching_bundle=matching_bundle)
    else:
        quality_score, quality_flags = predict_quality(
            resume_text,
            lang,
            sections,
            None,
            quality_bundle,
            neural_allowed=allow_quality_neural,
        )
        matching_score = 0
        if job_text:
            matching_score, _ = predict_matching(resume_text, job_text, lang, matching_bundle=matching_bundle)

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

    thin_profile = is_thin_student_or_intern_profile(resume_data)
    q_cap = quality_score_cap(completeness)
    quality_score = min(quality_score, q_cap)
    if thin_profile:
        quality_score = min(quality_score, 58)
    if job_text:
        matching_score = min(matching_score, matching_score_cap(completeness))
        if thin_profile:
            matching_score = min(matching_score, 60)

    insights = derive_insights(
        final_label,
        quality_flags,
        sections,
        resume_text,
        completeness_level=level,
        resume_data=resume_data,
        signals=rs,
    )
    recommendations = build_recommendations(insights, lang)

    overall_quality = min(100, max(0, int(quality_score)))

    result = AnalysisResult(
        score=overall_quality,
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
            "completeness": {
                "score": completeness["score"],
                "level": completeness["level"],
                "confidence": "low" if level != "adequate" else "high",
            },
            "scoreMeaning": "analysis.scoreMeaning.resume_quality",
            "seniorityClass": final_label,
            "seniorityConfidence": seniority_confidence,
            "seniorityEvidence": seniority_evidence[:12],
            "seniorityMlStatus": ml_status,
            "seniorityRuleBase": base_label,
            "insufficientData": rs.insufficient_data,
            "gatingReasons": list(rs.reasons),
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
