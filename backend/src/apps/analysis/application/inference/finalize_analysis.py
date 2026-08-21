"""
A etapa final da análise: caps, insights, score geral, telemetria e a linha de persistência.

Uma função só porque é uma fase só — depois que os três pilares respondem, nada aqui decide nada,
só monta. Fica fora do ``orchestrator.py`` para que aquele arquivo mostre o pipeline em vez de
esconder a montagem no fim dele.

A assinatura é longa de propósito: são os valores que os pilares produziram, cada um nomeado. A
alternativa seria um dicionário de contexto, que esconderia o mesmo acoplamento com menos ajuda do
verificador de tipos.
"""
from __future__ import annotations

from typing import Any

from .overall_score import compute_overall_score
from .postprocess.finalize import apply_completeness_caps, decorate_insights
from .postprocess.insights import derive_insights
from .postprocess.recommendations import build_recommendations
from .resolve_quality import _dimension_score
from .tasks.seniority.constants import SENIORITY_POLICY_VERSION
from .telemetry import build_debug_block, build_payload_body
from .types import AnalysisResult, build_persist_payload


def finalize_analysis(
    *,
    base_label: Any,
    career_sw: Any,
    completeness: Any,
    config: Any,
    dataset_version: Any,
    final_label: Any,
    fit_embedding_score: Any,
    fit_score: Any,
    fit_signals_score: Any,
    insight_gain_table: Any,
    integrity: Any,
    job_text: Any,
    lang: Any,
    matching_score: Any,
    quality_score: Any,
    level: Any,
    ml_status: Any,
    model_metadata_by_task: Any,
    model_name: Any,
    model_version: Any,
    provider: Any,
    qm: Any,
    quality_flags: Any,
    resume_data: Any,
    resume_text: Any,
    rs: Any,
    sections: Any,
    seniority_confidence: Any,
    seniority_evidence: Any,
    seniority_label_source: Any,
    seniority_score: Any,
    target_fit_extra: Any,
    target_fit_task: Any,
    target_pos: Any,
    text_pred: Any,
    tf_imp: Any,
    was_truncated: Any,
) -> dict[str, Any]:
    quality_score, matching_score, q_cap, _thin_profile = apply_completeness_caps(
        quality_score=quality_score,
        matching_score=matching_score,
        completeness=completeness,
        resume_data=resume_data,
        job_text=job_text,
    )

    insights = derive_insights(
        final_label,
        quality_flags,
        sections,
        resume_text,
        completeness_level=level,
        resume_data=resume_data,
        signals=rs,
        gain_table=insight_gain_table,
    )
    insights = decorate_insights(insights, target_fit_improvement=tf_imp, career_switch=career_sw)
    recommendations = build_recommendations(insights, lang)

    target_fit_for_overall: float | None = float(fit_score) if target_pos else None
    overall_quality, overall_formula_meta = compute_overall_score(
        float(quality_score),
        float(seniority_score),
        target_fit_for_overall,
        blend_enabled=bool(config.get("overall_blend_enabled")),
        w_quality=float(config.get("overall_w_quality") or 0.78),
        w_seniority=float(config.get("overall_w_seniority") or 0.12),
        w_target=float(config.get("overall_w_target_fit") or 0.10),
    )

    debug_block = build_debug_block(
        quality_score=quality_score,
        seniority_score=seniority_score,
        matching_score=matching_score,
        job_text=job_text,
        target_pos=target_pos,
        target_fit_task=target_fit_task,
        fit_signals_score=fit_signals_score,
        fit_embedding_score=fit_embedding_score,
        overall_formula_meta=overall_formula_meta,
        level=level,
        rs=rs,
        ml_status=ml_status,
        text_pred=text_pred,
        config=config,
    )

    payload_body = build_payload_body(
        insights=insights,
        recommendations=recommendations,
        was_truncated=was_truncated,
        model_metadata_by_task=model_metadata_by_task,
        completeness=completeness,
        level=level,
        final_label=final_label,
        seniority_confidence=seniority_confidence,
        seniority_evidence=seniority_evidence,
        ml_status=ml_status,
        base_label=base_label,
        rs=rs,
        target_fit_extra=target_fit_extra,
        debug_block=debug_block,
        integrity=integrity,
    )

    result = AnalysisResult(
        score=overall_quality,
        task_scores={
            # Each dimension the quality probe carries its own head for answers for itself. Without a
            # probe they stay copies of the headline score, which is what they always were.
            "ats": _dimension_score(qm, "ats", quality_score, q_cap),
            "clarity": _dimension_score(qm, "clarity", quality_score, q_cap),
            "seniority": seniority_score,
            "matching": matching_score if job_text else None,
            **target_fit_task,
        },
        insights=insights,
        recommendations=recommendations,
        metadata={
            "modelName": model_name,
            "modelVersion": model_version,
            "datasetVersion": dataset_version,
            "provider": provider if provider != "heuristics-only" else "heuristics",
        },
        payload_json=payload_body,
    )

    return build_persist_payload(
        result,
        rs=rs,
        base_label=base_label,
        final_label=final_label,
        seniority_label_source=seniority_label_source,
        seniority_policy_version=SENIORITY_POLICY_VERSION,
        seniority_confidence=seniority_confidence,
        seniority_evidence=seniority_evidence,
        text_pred=text_pred,
        target_pos=target_pos,
        fit_embedding_score=fit_embedding_score,
        fit_signals_score=fit_signals_score,
        fit_score=fit_score,
    )
