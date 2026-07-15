"""
Pure builders for analysis telemetry: metadata, debug, and payload assembly.

Receive already-computed results only — never recalculate scores or labels.
"""
from __future__ import annotations

from typing import Any


def normalize_provider(provider: str | None) -> str:
    provider = str(provider or "local").strip() or "local"
    return "heuristics" if provider == "heuristics-only" else provider


def build_task_metadata(
    task: str,
    bundle_extra: dict[str, Any] | None,
    config: dict[str, Any],
) -> dict[str, str]:
    extra = bundle_extra or {}
    metadata = extra.get("metadata") if isinstance(extra.get("metadata"), dict) else {}
    provider = normalize_provider(extra.get("provider"))
    configured_version = (config.get("model_version_by_task") or {}).get(task) or config.get(
        "model_version", "analysis_v1"
    )
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


def build_model_metadata_by_task(
    *,
    config: dict[str, Any],
    metadata_seniority: dict[str, Any],
    metadata_quality: dict[str, Any],
    metadata_matching: dict[str, Any],
    job_text: str,
    target_pos: str,
    target_fit_bundle_extra: dict[str, Any] | None,
) -> dict[str, dict[str, str]]:
    model_metadata_by_task = {
        "seniority": build_task_metadata("seniority", metadata_seniority, config),
        "quality": build_task_metadata("quality", metadata_quality, config),
    }
    if job_text:
        model_metadata_by_task["matching"] = build_task_metadata("matching", metadata_matching, config)
    if target_pos and target_fit_bundle_extra is not None:
        model_metadata_by_task["target_fit"] = build_task_metadata(
            "target_fit", target_fit_bundle_extra, config
        )
    return model_metadata_by_task


def resolve_top_level_model_meta(
    *,
    config: dict[str, Any],
    metadata_seniority: dict[str, Any],
    metadata_quality: dict[str, Any],
) -> tuple[str, str, str, str]:
    """Return (model_name, model_version, dataset_version, provider)."""
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
    return model_name, model_version, dataset_version, provider


def build_debug_block(
    *,
    quality_score: int,
    seniority_score: int,
    matching_score: int,
    job_text: str,
    target_pos: str,
    target_fit_task: dict[str, float | None],
    fit_signals_score: int,
    fit_embedding_score: int | None,
    overall_formula_meta: dict[str, Any],
    level: str,
    rs: Any,
    ml_status: str,
    text_pred: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    tf_dbg = None
    tf_sig_dbg = None
    tf_emb_dbg = None
    if target_pos:
        tf_dbg = float(target_fit_task.get("target_fit") or 0)
        tf_sig_dbg = int(fit_signals_score)
        tf_emb_dbg = fit_embedding_score
    return {
        "scoreBreakdown": {
            "quality_score": int(quality_score),
            "seniority_general_score": int(seniority_score),
            "target_fit_score": tf_dbg,
            "target_fit_signals_score": tf_sig_dbg,
            "target_fit_embedding_score": tf_emb_dbg,
            "matching_score": int(matching_score) if job_text else None,
            "overall_weights": overall_formula_meta.get("weights"),
            "overall_formula": overall_formula_meta.get("formula"),
            "overall_mode": overall_formula_meta.get("mode"),
        },
        "featureSnapshot": {
            "completenessLevel": level,
            "completenessScore": int(rs.completeness_score or 0),
            "wordCount": int(rs.word_count or 0),
            "experiencesCount": int(rs.experiences_count or 0),
            "totalMonthsExperience": int(rs.total_months_experience or 0),
            "skillsCount": int(rs.skills_count or 0),
            "bulletsCount": int(rs.bullets_count or 0),
            "seniorityMlStatus": ml_status,
            "textSenioritySource": text_pred.get("source"),
            "embeddingsEnabled": bool(config.get("embeddings_enabled")),
        },
    }


def build_payload_body(
    *,
    insights: dict[str, Any],
    recommendations: list[dict[str, Any]],
    was_truncated: bool,
    model_metadata_by_task: dict[str, Any],
    completeness: dict[str, Any],
    level: str,
    final_label: str,
    seniority_confidence: str,
    seniority_evidence: list[Any],
    ml_status: str,
    base_label: str,
    rs: Any,
    target_fit_extra: dict[str, Any],
    debug_block: dict[str, Any] | None,
) -> dict[str, Any]:
    payload_body: dict[str, Any] = {
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
        **target_fit_extra,
    }
    if debug_block is not None:
        payload_body["debug"] = debug_block
    return payload_body


def target_fit_improvement(missing_terms: list[str], lang: str) -> dict[str, Any] | None:
    if not missing_terms:
        return None
    shown = ", ".join(missing_terms[:6])
    if not shown:
        return None
    return {
        "key": "analysis.insights.improvements.target_role_terms",
        "priority": "high",
        "params": {"terms": shown, "lang": lang},
    }
