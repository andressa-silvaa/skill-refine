"""
Orchestrator: analyze_resume(resume_data, job_description_text, language) -> AnalysisResult.
Quality (currículo) is separate from senioridade (estimativa). Score principal = qualidade.

The per-pillar resolvers live in ``resolve_seniority.py``, ``resolve_target_fit.py`` and
``resolve_quality.py``. ``SENIORITY_TO_SCORE`` and ``_domain_block`` are re-exported here because
the tests import them from this module.
"""
from __future__ import annotations

from apps.analysis.application.seniority_persist import build_seniority_evidence_json
from django.conf import settings
from typing import Any
from .completeness import matching_score_cap, quality_score_cap
from .config import get_config
from .integrity import build_integrity_block
from .language_detection import detect_language, get_language_detector
from .overall_score import compute_overall_score
from .postprocess.insight_ranking import (
    FALLBACK_PROVIDER as INSIGHT_RANKING_FALLBACK,
    PROVIDER as INSIGHT_RANKING_PROVIDER,
    load_gain_table,
)
from .postprocess.finalize import apply_completeness_caps, decorate_insights
from .postprocess.insights import derive_insights
from .postprocess.recommendations import build_recommendations
from .resume_mapper import resume_to_text
from .resume_signals import is_thin_student_or_intern_profile
from .safety import truncate_text
from .signals import extract_resume_signals
from .tasks.quality.bullet_flags import predict_bullet_flags
from .tasks.quality.loader_bullet_probe import get_bullet_probe_bundle
from .tasks.seniority.constants import SENIORITY_POLICY_VERSION
from .tasks.target_fit.loader_embeddings import get_embeddings_model
from .telemetry import (
    build_debug_block,
    build_model_metadata_by_task,
    build_payload_body,
    resolve_top_level_model_meta,
)
from .finalize_analysis import finalize_analysis

import logging

from .resolve_quality import _dimension_score, _matching_extra, _resolve_quality_and_matching
from .resolve_seniority import SENIORITY_TO_SCORE, _resolve_seniority
from .resolve_target_fit import _domain_block, _resolve_target_fit

logger = logging.getLogger(__name__)

def analyze_resume(
    resume_data: dict[str, Any],
    job_description_text: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """
    Full analysis pipeline. Returns dict for ResumeAnalysis persistence.
    """
    config = get_config(settings)
    preferred_lang = (language or "pt-BR").strip()
    max_resume = config["max_chars_resume"]
    max_job = config["max_chars_job"]

    # Detect before anything reads `lang`: the ESCO index, the section renderer and the insight copy
    # all key off it, and `language` is only the user's interface preference (see worker.py).
    lang, language_provider, _language_confidence = detect_language(
        get_language_detector(config),
        resume_to_text(resume_data, language=preferred_lang).full_text,
        preferred_lang,
    )

    sections = resume_to_text(resume_data, language=lang)
    resume_text = sections.full_text
    resume_text, was_truncated = truncate_text(resume_text, max_resume)

    shared_encoder = get_embeddings_model(settings) if config.get("embeddings_enabled") else None
    bullet_detail = predict_bullet_flags(
        get_bullet_probe_bundle(config), shared_encoder, resume_data
    )
    insight_gain_table = load_gain_table(config)
    rs = extract_resume_signals(
        resume_data,
        sections,
        language=lang,
        leadership_override=(
            bool(bullet_detail["flags"]["has_leadership"]) if bullet_detail else None
        ),
    )
    completeness = {"score": rs.completeness_score, "level": rs.completeness_level}
    level = rs.completeness_level

    allow_quality_neural = level != "insufficient"

    seniority = _resolve_seniority(
        resume_data=resume_data,
        resume_text=resume_text,
        lang=lang,
        config=config,
        rs=rs,
        encoder=shared_encoder,
    )
    base_label = seniority["base_label"]
    final_label = seniority["final_label"]
    seniority_confidence = seniority["seniority_confidence"]
    seniority_evidence = seniority["seniority_evidence"]
    ml_status = seniority["ml_status"]
    model_bundle = seniority["model_bundle"]
    sanitized_cv = seniority["sanitized_cv"]
    text_pred = seniority["text_pred"]
    seniority_label_source = seniority["seniority_label_source"]
    seniority_score = seniority["seniority_score"]

    job_text_raw = (job_description_text or "").strip()
    job_text = ""
    if job_text_raw:
        job_text, _ = truncate_text(job_text_raw, max_job)

    target_fit = _resolve_target_fit(
        resume_data=resume_data,
        resume_text=resume_text,
        sections=sections,
        job_text=job_text,
        lang=lang,
        config=config,
        rs=rs,
        final_label=final_label,
        sanitized_cv=sanitized_cv,
        encoder=shared_encoder,
    )
    target_pos = target_fit["target_pos"]
    fit_score = target_fit["fit_score"]
    fit_signals_score = target_fit["fit_signals_score"]
    fit_embedding_score = target_fit["fit_embedding_score"]
    career_sw = target_fit["career_sw"]
    tf_imp = target_fit["tf_imp"]
    target_fit_extra = target_fit["target_fit_extra"]
    target_fit_task = target_fit["target_fit_task"]
    target_fit_bundle_extra = target_fit["target_fit_bundle_extra"]

    qm = _resolve_quality_and_matching(
        resume_data=resume_data,
        resume_text=resume_text,
        job_text=job_text,
        lang=lang,
        sections=sections,
        config=config,
        final_label=final_label,
        allow_quality_neural=allow_quality_neural,
        bullet_detail=bullet_detail,
        encoder=shared_encoder,
    )
    quality_bundle = qm["quality_bundle"]
    matching_bundle = qm["matching_bundle"]
    quality_score = qm["quality_score"]
    quality_flags = qm["quality_flags"]
    matching_score = qm["matching_score"]

    metadata_seniority = model_bundle[1] if isinstance(model_bundle[1], dict) else {}
    metadata_quality = quality_bundle[1] if isinstance(quality_bundle, tuple) and isinstance(quality_bundle[1], dict) else {}
    if isinstance(qm.get("quality_extra"), dict):
        metadata_quality = qm["quality_extra"]
    metadata_matching = qm.get("matching_extra")
    if not isinstance(metadata_matching, dict):
        metadata_matching = (
            matching_bundle[1]
            if isinstance(matching_bundle, tuple) and isinstance(matching_bundle[1], dict)
            else {}
        )
    model_metadata_by_task = build_model_metadata_by_task(
        config=config,
        metadata_seniority=metadata_seniority,
        metadata_quality=metadata_quality,
        metadata_matching=metadata_matching,
        job_text=job_text,
        target_pos=target_pos,
        target_fit_bundle_extra=target_fit_bundle_extra,
        flags_provider=str(qm["quality_detail"].get("flags_provider") or ""),
        insight_ranking_provider=(
            INSIGHT_RANKING_PROVIDER if insight_gain_table else INSIGHT_RANKING_FALLBACK
        ),
        language_provider=language_provider,
    )
    model_name, model_version, dataset_version, provider = resolve_top_level_model_meta(
        config=config,
        metadata_seniority=metadata_seniority,
        metadata_quality=metadata_quality,
    )
    integrity = build_integrity_block(
        {
            task: str((meta or {}).get("provider") or "")
            for task, meta in model_metadata_by_task.items()
        },
        low_confidence_tasks=(
            ["quality"] if qm["quality_detail"].get("confidence") == "low" else []
        ),
    )
    return finalize_analysis(
        base_label=base_label,
        career_sw=career_sw,
        completeness=completeness,
        config=config,
        dataset_version=dataset_version,
        final_label=final_label,
        fit_embedding_score=fit_embedding_score,
        fit_score=fit_score,
        fit_signals_score=fit_signals_score,
        insight_gain_table=insight_gain_table,
        integrity=integrity,
        job_text=job_text,
        lang=lang,
        matching_score=matching_score,
        quality_score=quality_score,
        level=level,
        ml_status=ml_status,
        model_metadata_by_task=model_metadata_by_task,
        model_name=model_name,
        model_version=model_version,
        provider=provider,
        qm=qm,
        quality_flags=quality_flags,
        resume_data=resume_data,
        resume_text=resume_text,
        rs=rs,
        sections=sections,
        seniority_confidence=seniority_confidence,
        seniority_evidence=seniority_evidence,
        seniority_label_source=seniority_label_source,
        seniority_score=seniority_score,
        target_fit_extra=target_fit_extra,
        target_fit_task=target_fit_task,
        target_pos=target_pos,
        text_pred=text_pred,
        tf_imp=tf_imp,
        was_truncated=was_truncated,
    )
