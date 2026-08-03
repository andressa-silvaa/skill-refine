"""
Orchestrator: analyze_resume(resume_data, job_description_text, language) -> AnalysisResult.
Quality (currículo) is separate from senioridade (estimativa). Score principal = qualidade.
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from apps.analysis.application.seniority_persist import build_seniority_evidence_json

from .cascade import CascadeResult, run_cascade
from .completeness import matching_score_cap, quality_score_cap
from .config import get_config, get_signals_ml_thresholds
from .loader import get_matching_bundle, get_model_bundle, get_quality_bundle
from .loader_signals_model import get_signals_ml_bundle, signals_ml_metadata_for_extra
from .overall_score import compute_overall_score
from .postprocess.insights import derive_insights
from .postprocess.llm_feedback import generate_ai_feedback
from .postprocess.recommendations import build_recommendations
from .resume_mapper import resume_to_text
from .resume_signals import is_thin_student_or_intern_profile
from .safety import truncate_text
from .signals import extract_resume_signals
from .tasks.matching import predict_matching
from .tasks.quality import predict_quality
from .tasks.seniority import (
    SENIORITY_LABELS,
    clamp_seniority_vetoes,
    predict_hf_seniority_probs,
    rule_based_seniority,
    signals_ml_predict,
)
from .tasks.seniority.constants import SENIORITY_POLICY_VERSION
from .tasks.seniority.text import (
    fuse_seniority,
    get_text_seniority_bundle,
    predict_text_seniority,
    structural_signals_strength,
)
from .tasks.target_fit import (
    TARGET_FIT_POLICY_VERSION,
    compute_career_switch,
    compute_target_fit_policy,
    compute_target_seniority,
    extract_target_fit_signals,
    infer_domain_category,
)
from .tasks.target_fit.embedding import (
    build_cv_embedding_text,
    build_target_embedding_text,
    embedding_fit_scores,
)
from .tasks.target_fit.loader_embeddings import get_embeddings_model
from .tasks.target_fit.loader_ml import (
    get_target_fit_ml_bundle,
    predict_target_fit_ml_score,
    target_fit_ml_metadata_for_task,
)
from .telemetry import (
    build_debug_block,
    build_model_metadata_by_task,
    build_payload_body,
    resolve_top_level_model_meta,
    target_fit_improvement,
)
from .text_sanitizer import job_text_sanitized, resume_to_text_sanitized
from .types import AnalysisResult

logger = logging.getLogger(__name__)

SENIORITY_TO_SCORE = {"intern": 25, "junior": 50, "mid": 75, "senior": 100}


def _quality_needs_seniority_first(quality_bundle: tuple[Any, dict] | None) -> bool:
    if not quality_bundle:
        return False
    model_or_none, extra = quality_bundle
    if not isinstance(extra, dict):
        return False
    return extra.get("kind") == "hybrid" and model_or_none is not None


def _resolve_seniority(
    *,
    resume_data: dict[str, Any],
    resume_text: str,
    lang: str,
    config: dict[str, Any],
    rs: Any,
    allow_ml_seniority: bool,
) -> dict[str, Any]:
    base_label, base_confidence, base_evidence = rule_based_seniority(rs)

    language_mode = "multi" if config["multilang"] else "mono"
    signals_bundle = get_signals_ml_bundle(config)
    signals_bundle_used: dict | None = None

    def _rule_policy_result(*, ml_status: str, extra_evidence: list | None = None) -> CascadeResult:
        fl, ve = clamp_seniority_vetoes(base_label, rs)
        evidence = list(base_evidence) + list(extra_evidence or []) + ve
        return CascadeResult(
            value=fl,
            provider="rule_policy",
            status="applied",
            evidence=evidence,
            extra={"confidence": base_confidence, "ml_status": ml_status},
        )

    def _step_signals_ml() -> CascadeResult | None:
        nonlocal signals_bundle_used
        if not signals_bundle:
            return None
        sm_cfg = get_signals_ml_thresholds(settings, bundle_metadata=signals_bundle.get("_metadata"))
        ml_lab, ml_conf, _probs, ml_ev, st = signals_ml_predict(signals_bundle, rs, sm_cfg)
        if st == "applied":
            merged_evidence = list(base_evidence) + list(ml_ev)
            fl, veto_ev = clamp_seniority_vetoes(ml_lab, rs)
            merged_evidence.extend(veto_ev)
            signals_bundle_used = signals_bundle
            return CascadeResult(
                value=fl,
                provider="signals_ml",
                status="applied",
                evidence=merged_evidence,
                extra={"confidence": ml_conf, "ml_status": "applied_signals_ml"},
            )
        if st == "error":
            return _rule_policy_result(ml_status="signals_ml_error")
        return _rule_policy_result(ml_status=f"skipped_signals_ml:{st}", extra_evidence=list(ml_ev))

    cascade = run_cascade(
        [_step_signals_ml],
        default=_rule_policy_result(ml_status="skipped_no_signals_ml_bundle"),
    )

    final_label = cascade.value
    seniority_confidence = cascade.extra.get("confidence", base_confidence)
    seniority_evidence = list(cascade.evidence or [])
    ml_status = cascade.extra.get("ml_status", "skipped_no_model")

    if ml_status == "applied_signals_ml" and signals_bundle_used is not None:
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
        model_bundle = (
            None,
            {
                "labels": list(SENIORITY_LABELS),
                "metadata": {
                    "model_name_base": "rule_policy",
                    "model_version": SENIORITY_POLICY_VERSION,
                    "dataset_version": "",
                },
                "provider": "rule_policy",
            },
        )

    hf_bundle = get_model_bundle(task="seniority", language_mode=language_mode, language=lang, config=config)
    hf_lab, hf_gap, hf_prov = predict_hf_seniority_probs(resume_text, lang, hf_bundle, allow=allow_ml_seniority)
    if hf_lab:
        seniority_evidence.append(
            {
                "type": "ml_suggestion",
                "label": hf_lab,
                "gap": round(float(hf_gap), 4),
                "provider": hf_prov,
            }
        )

    sanitized_cv = resume_to_text_sanitized(resume_data)
    text_pred: dict[str, Any] = {"label": None, "confidence": "low", "probs": {}, "source": "none"}
    fuse_meta: dict[str, Any] = {}
    seniority_label_source = "rule_policy"
    if ml_status == "applied_signals_ml":
        seniority_label_source = "signals_ml"

    if config["text_seniority_fusion_enabled"]:
        tbundle = get_text_seniority_bundle(settings) if config["text_seniority_enabled"] else None
        text_pred = predict_text_seniority(
            sanitized_cv,
            lang,
            tbundle,
            allow_lexical_fallback=True,
        )
        strength = structural_signals_strength(
            total_months_experience=rs.total_months_experience,
            experiences_count=rs.experiences_count,
        )
        text_suggests_senior = text_pred.get("label") == "senior"
        fused_label, fused_conf, fuse_meta = fuse_seniority(
            final_label,
            seniority_confidence,
            text_pred.get("label"),
            str(text_pred.get("confidence") or "low"),
            strength,
            has_leadership_terms=bool(rs.has_leadership_terms),
            total_months_experience=int(rs.total_months_experience or 0),
            text_suggests_senior=text_suggests_senior,
        )
        final_label = fused_label
        seniority_confidence = fused_conf
        if fuse_meta.get("fusion") == "signals_ml_text":
            seniority_label_source = "fused"
        if text_pred.get("label") or text_pred.get("source") not in ("none",):
            seniority_evidence.append(
                {
                    "type": "text_seniority",
                    "label": text_pred.get("label"),
                    "confidence": text_pred.get("confidence"),
                    "source": text_pred.get("source"),
                    "fusionWeights": fuse_meta.get("weights"),
                }
            )

    seniority_score = SENIORITY_TO_SCORE.get(final_label, 50)
    return {
        "base_label": base_label,
        "final_label": final_label,
        "seniority_confidence": seniority_confidence,
        "seniority_evidence": seniority_evidence,
        "ml_status": ml_status,
        "model_bundle": model_bundle,
        "sanitized_cv": sanitized_cv,
        "text_pred": text_pred,
        "fuse_meta": fuse_meta,
        "seniority_label_source": seniority_label_source,
        "seniority_score": seniority_score,
    }


def _resolve_target_fit(
    *,
    resume_data: dict[str, Any],
    resume_text: str,
    sections: Any,
    job_text: str,
    lang: str,
    config: dict[str, Any],
    rs: Any,
    final_label: str,
    sanitized_cv: str,
) -> dict[str, Any]:
    data_block = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else {}
    target_pos = str(data_block.get("targetPosition") or "").strip()

    fit_score = 0
    fit_signals_score = 0
    fit_embedding_score: int | None = None
    target_seniority_label = final_label
    ts_pack: dict = {"targetSeniorityLabel": final_label, "clampReasonKeys": []}
    career_sw: dict = {"detected": False, "reasonKey": ""}
    tf_imp = None
    tf_signals = None
    domain_target: dict = {"domainCategory": "general", "confidence": "low", "evidenceTokens": []}
    domain_resume: dict = {"domainCategory": "general", "confidence": "low", "evidenceTokens": []}
    target_fit_extra: dict[str, Any] = {}
    target_fit_task: dict[str, float | None] = {"target_fit": None, "target_seniority": None}
    target_fit_bundle_extra: dict[str, Any] | None = None

    if not target_pos:
        return {
            "target_pos": target_pos,
            "fit_score": fit_score,
            "fit_signals_score": fit_signals_score,
            "fit_embedding_score": fit_embedding_score,
            "target_seniority_label": target_seniority_label,
            "ts_pack": ts_pack,
            "career_sw": career_sw,
            "tf_imp": tf_imp,
            "target_fit_extra": target_fit_extra,
            "target_fit_task": target_fit_task,
            "target_fit_bundle_extra": target_fit_bundle_extra,
        }

    domain_target = infer_domain_category(f"{target_pos} {job_text}".strip(), lang=lang)
    resume_domain_text = (resume_text[:12000] if resume_text else "") or sections.full_text[:12000]
    domain_resume = infer_domain_category(resume_domain_text, lang=lang)
    tf_signals = extract_target_fit_signals(
        resume_data,
        target_pos,
        job_text if job_text else None,
        lang,
        completeness_score=int(rs.completeness_score or 0),
    )
    rd_cat = str(domain_resume.get("domainCategory") or "general")
    td_cat = str(domain_target.get("domainCategory") or "general")
    policy_score = compute_target_fit_policy(
        tf_signals,
        has_job_text=bool(job_text),
        resume_domain=rd_cat,
        target_domain=td_cat,
    )

    policy_extra = {
        "provider": "target_fit_policy",
        "metadata": {
            "model_name_base": "target_fit_policy",
            "model_version": TARGET_FIT_POLICY_VERSION,
            "dataset_version": "",
        },
    }

    def _step_target_fit_ml() -> CascadeResult | None:
        tf_ml_bundle = get_target_fit_ml_bundle(config)
        if not tf_ml_bundle:
            return CascadeResult(value=None, provider="target_fit_ml", status="skipped_no_model")
        try:
            score = predict_target_fit_ml_score(
                tf_ml_bundle,
                signals=tf_signals,
                resume_domain=rd_cat,
                target_domain=td_cat,
                has_job_text=bool(job_text),
            )
            md_flat = target_fit_ml_metadata_for_task(tf_ml_bundle)
            return CascadeResult(
                value=int(score),
                provider="target_fit_ml",
                status="applied",
                extra={
                    "bundle_extra": {
                        "provider": "target_fit_ml",
                        "metadata": {
                            "model_name_base": md_flat.get("model_name_base") or "target_fit_signals",
                            "model_version": md_flat.get("model_version") or "",
                            "dataset_version": md_flat.get("dataset_version") or "",
                        },
                    }
                },
            )
        except Exception as exc:
            logger.warning("target_fit_ml inference failed, using policy: %s", exc)
            return CascadeResult(
                value=None,
                provider="target_fit_ml",
                status="error",
                evidence={"error": str(exc)},
            )

    def _step_target_fit_policy() -> CascadeResult:
        return CascadeResult(
            value=int(policy_score),
            provider="target_fit_policy",
            status="applied",
            extra={"bundle_extra": policy_extra},
        )

    # Canonical cascade: ML (if available) then policy fallback — same order as before.
    cascade = run_cascade(
        [_step_target_fit_ml, _step_target_fit_policy],
        default=_step_target_fit_policy(),
    )
    fit_score = int(cascade.value)
    target_fit_bundle_extra = (cascade.extra or {}).get("bundle_extra") or policy_extra

    fit_signals_score = int(fit_score)
    fit_embedding_score = None
    semantic_kw: list[str] = []
    emb_model = get_embeddings_model(settings) if config.get("embeddings_enabled") else None
    if emb_model is not None:
        try:
            cv_emb_text = build_cv_embedding_text(sanitized_cv)
            jt_san = job_text_sanitized(job_text) if job_text else ""
            tgt_txt = build_target_embedding_text(target_pos, jt_san, td_cat, lang)
            fit_embedding_score, _cos, semantic_kw = embedding_fit_scores(emb_model, cv_emb_text, tgt_txt)
            w_e = float(config.get("target_fit_embed_weight") or 0.65)
            w_e = max(0.0, min(1.0, w_e))
            fit_final = w_e * float(fit_embedding_score or 0) + (1.0 - w_e) * float(fit_signals_score)
            fit_score = int(round(max(0, min(100, fit_final))))
            emb_name = str(getattr(settings, "ANALYSIS_EMBEDDINGS_MODEL_NAME", "") or "MiniLM").split("/")[-1][:48]
            target_fit_bundle_extra = {
                "provider": "target_fit_embedding_v1",
                "metadata": {
                    "model_name_base": emb_name,
                    "model_version": "target_fit_embedding_v1",
                    "dataset_version": "",
                },
            }
        except Exception as exc:
            logger.warning("target_fit embedding failed, using signals only: %s", exc)
            fit_embedding_score = None
            semantic_kw = []
    ts_pack = compute_target_seniority(final_label, fit_score, tf_signals, lang)
    target_seniority_label = str(ts_pack.get("targetSeniorityLabel") or "junior")
    career_sw = compute_career_switch(
        final_label,
        fit_score,
        str(domain_resume.get("domainCategory") or "general"),
        str(domain_target.get("domainCategory") or "general"),
    )
    tf_imp = target_fit_improvement(tf_signals.required_terms_missing, lang)
    target_fit_task = {
        "target_fit": float(fit_score),
        "target_seniority": float(SENIORITY_TO_SCORE.get(target_seniority_label, 50)),
    }
    tfe: dict[str, Any] = {
        "matchedTerms": tf_signals.required_terms_matched,
        "missingTerms": tf_signals.required_terms_missing,
        "matchedSkills": tf_signals.skills_matched,
        "experienceKeywordHits": tf_signals.experience_keyword_hits,
        "educationAlignment": tf_signals.education_alignment,
        "portfolioEvidence": tf_signals.portfolio_evidence,
        "requiredTermsHit": tf_signals.required_terms_hit,
        "requiredTermsTotal": tf_signals.required_terms_total,
        "skillsHit": tf_signals.skills_hit,
    }
    if semantic_kw:
        tfe["semanticEvidence"] = {"keywords": semantic_kw}
    target_fit_extra = {
        "targetFitScore": int(fit_score),
        "targetFitSignalsScore": int(fit_signals_score),
        "targetFitEmbeddingScore": fit_embedding_score,
        "targetFitFinalScore": int(fit_score),
        "targetSeniorityLabel": target_seniority_label,
        "targetSeniorityClampReasons": list(ts_pack.get("clampReasonKeys") or []),
        "targetRoleDomain": {
            "category": domain_target.get("domainCategory"),
            "confidence": domain_target.get("confidence"),
            "evidenceTokens": list(domain_target.get("evidenceTokens") or [])[:8],
        },
        "resumeDomain": {
            "category": domain_resume.get("domainCategory"),
            "confidence": domain_resume.get("confidence"),
            "evidenceTokens": list(domain_resume.get("evidenceTokens") or [])[:8],
        },
        "targetFitEvidence": tfe,
        "careerSwitch": {
            "detected": bool(career_sw.get("detected")),
            "reasonKey": str(career_sw.get("reasonKey") or ""),
        },
    }
    if target_fit_bundle_extra:
        meta_blk = target_fit_bundle_extra.get("metadata") or {}
        target_fit_extra["targetFitProvider"] = str(target_fit_bundle_extra.get("provider") or "target_fit_policy")
        target_fit_extra["targetFitModelVersion"] = str(meta_blk.get("model_version") or "")
        target_fit_extra["targetFitDatasetVersion"] = str(meta_blk.get("dataset_version") or "")

    return {
        "target_pos": target_pos,
        "fit_score": fit_score,
        "fit_signals_score": fit_signals_score,
        "fit_embedding_score": fit_embedding_score,
        "target_seniority_label": target_seniority_label,
        "ts_pack": ts_pack,
        "career_sw": career_sw,
        "tf_imp": tf_imp,
        "target_fit_extra": target_fit_extra,
        "target_fit_task": target_fit_task,
        "target_fit_bundle_extra": target_fit_bundle_extra,
    }


def _resolve_quality_and_matching(
    *,
    resume_text: str,
    job_text: str,
    lang: str,
    sections: Any,
    config: dict[str, Any],
    final_label: str,
    allow_quality_neural: bool,
) -> dict[str, Any]:
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

    return {
        "quality_bundle": quality_bundle,
        "matching_bundle": matching_bundle,
        "quality_score": quality_score,
        "quality_flags": quality_flags,
        "matching_score": matching_score,
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

    seniority = _resolve_seniority(
        resume_data=resume_data,
        resume_text=resume_text,
        lang=lang,
        config=config,
        rs=rs,
        allow_ml_seniority=allow_ml_seniority,
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
        resume_text=resume_text,
        job_text=job_text,
        lang=lang,
        sections=sections,
        config=config,
        final_label=final_label,
        allow_quality_neural=allow_quality_neural,
    )
    quality_bundle = qm["quality_bundle"]
    matching_bundle = qm["matching_bundle"]
    quality_score = qm["quality_score"]
    quality_flags = qm["quality_flags"]
    matching_score = qm["matching_score"]

    metadata_seniority = model_bundle[1] if isinstance(model_bundle[1], dict) else {}
    metadata_quality = quality_bundle[1] if isinstance(quality_bundle, tuple) and isinstance(quality_bundle[1], dict) else {}
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
    )
    model_name, model_version, dataset_version, provider = resolve_top_level_model_meta(
        config=config,
        metadata_seniority=metadata_seniority,
        metadata_quality=metadata_quality,
    )

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
    if tf_imp:
        improvements = list(insights.get("improvements") or [])
        improvements.insert(0, tf_imp)
        insights = {**insights, "improvements": improvements}
    if career_sw.get("detected"):
        strengths = list(insights.get("strengths") or [])
        strengths.insert(
            0,
            {
                "key": "analysis.insights.strengths.career_switch_context",
                "params": {"reasonKey": str(career_sw.get("reasonKey") or "")},
            },
        )
        insights = {**insights, "strengths": strengths}
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

    ai_feedback = generate_ai_feedback(
        resume_text=resume_text,
        seniority_label=final_label,
        quality_score=int(quality_score),
        target_fit_score=int(fit_score) if target_pos else None,
        target_position=target_pos,
        language=lang,
    )

    debug_block: dict[str, Any] | None = None
    if getattr(settings, "DEBUG", False):
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
        ai_feedback=ai_feedback,
    )

    result = AnalysisResult(
        score=overall_quality,
        task_scores={
            "ats": quality_score,
            "clarity": quality_score,
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

    d = result.to_persist_dict()
    return {
        "score": d["score"],
        "task_scores": d["task_scores"],
        "payload_json": d["payload_json"],
        "model_name": d["metadata"]["modelName"],
        "model_version": d["metadata"]["modelVersion"],
        "dataset_version": d["metadata"].get("datasetVersion", ""),
        "provider": d["metadata"]["provider"],
        "seniority_rule_label": base_label,
        "seniority_final_label": final_label,
        "seniority_label_source": seniority_label_source,
        "seniority_policy_version": SENIORITY_POLICY_VERSION,
        "seniority_confidence_persist": seniority_confidence
        if seniority_confidence in ("low", "medium", "high")
        else "low",
        "seniority_evidence_json": build_seniority_evidence_json(rs, seniority_evidence),
        "seniority_text_label": str(text_pred.get("label") or "")[:16],
        "seniority_text_confidence": str(text_pred.get("confidence") or "")[:16],
        "target_fit_embedding_score": (fit_embedding_score if target_pos else None),
        "target_fit_signals_score": (int(fit_signals_score) if target_pos else None),
        "target_fit_final_score": (int(fit_score) if target_pos else None),
    }
