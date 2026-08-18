"""
Target-fit resolution: encoder blended with the signals policy, plus the ESCO domain block.

The 0.65/0.35 blend is measured, not assumed: against adjacent-occupation negatives the mix scores
AUC 0.965 where the encoder alone scores 0.946 and the policy alone 0.924 
(ml/reports/target_fit_blend_v3.md).
"""
from __future__ import annotations

from django.conf import settings
from typing import Any
from .cascade import CascadeResult, run_cascade
from .tasks.target_fit import (
    TARGET_FIT_POLICY_VERSION,
    compute_career_switch,
    compute_target_fit_policy,
    extract_target_fit_signals,
    infer_domain_category,
)
from .tasks.target_fit.embedding import (
    build_cv_embedding_text,
    build_target_embedding_text,
    embedding_fit_scores,
)
from .tasks.target_fit.esco_retrieval import build_occupation_query
from .tasks.target_fit.loader_ml import (
    get_target_fit_ml_bundle,
    predict_target_fit_ml_score,
    target_fit_ml_metadata_for_task,
)
from .telemetry import target_fit_improvement
from .text_sanitizer import job_text_sanitized

import logging

logger = logging.getLogger(__name__)


def _domain_block(domain: dict[str, Any]) -> dict[str, Any]:
    """
    Public shape of a domain inference: the legacy contract, plus the ESCO enrichment only on the
    retrieval path — the keyword fallback keeps the exact shape consumers already receive.
    """
    block: dict[str, Any] = {
        "category": domain.get("domainCategory"),
        "confidence": domain.get("confidence"),
        "evidenceTokens": list(domain.get("evidenceTokens") or [])[:8],
    }
    occupation = domain.get("occupation") if isinstance(domain.get("occupation"), dict) else None
    if occupation:
        block["provider"] = str(domain.get("provider") or "domain_embeddings")
        block["escoOccupation"] = {
            "uri": occupation.get("uri") or "",
            "label": occupation.get("label") or "",
            "isco": occupation.get("isco") or "",
            "iscoGroup": occupation.get("iscoGroup") or "",
            "cosine": occupation.get("cosine"),
        }
        block["domainMargin"] = domain.get("domainMargin")
        block["occupationGap"] = domain.get("occupationGap")
    return block


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
    encoder: Any,
) -> dict[str, Any]:
    data_block = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else {}
    target_pos = str(data_block.get("targetPosition") or "").strip()

    fit_score = 0
    fit_signals_score = 0
    fit_embedding_score: int | None = None
    career_sw: dict = {"detected": False, "reasonKey": ""}
    tf_imp = None
    tf_signals = None
    domain_target: dict = {"domainCategory": "general", "confidence": "low", "evidenceTokens": []}
    domain_resume: dict = {"domainCategory": "general", "confidence": "low", "evidenceTokens": []}
    target_fit_extra: dict[str, Any] = {}
    target_fit_task: dict[str, float | None] = {"target_fit": None}
    target_fit_bundle_extra: dict[str, Any] | None = None

    if not target_pos:
        return {
            "target_pos": target_pos,
            "fit_score": fit_score,
            "fit_signals_score": fit_signals_score,
            "fit_embedding_score": fit_embedding_score,
            "career_sw": career_sw,
            "tf_imp": tf_imp,
            "target_fit_extra": target_fit_extra,
            "target_fit_task": target_fit_task,
            "target_fit_bundle_extra": target_fit_bundle_extra,
        }

    emb_model = encoder
    esco_model = emb_model if config.get("esco_domain_enabled") else None
    esco_options = config.get("esco_options") or {}

    domain_target = infer_domain_category(
        f"{target_pos} {job_text}".strip(),
        lang=lang,
        embeddings_model=esco_model,
        occupation_query=target_pos,
        esco_options=esco_options,
    )
    resume_domain_text = (resume_text[:12000] if resume_text else "") or sections.full_text[:12000]
    domain_resume = infer_domain_category(
        resume_domain_text,
        lang=lang,
        embeddings_model=esco_model,
        occupation_query=build_occupation_query(resume_data),
        esco_options=esco_options,
    )
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
    career_sw = compute_career_switch(
        final_label,
        fit_score,
        str(domain_resume.get("domainCategory") or "general"),
        str(domain_target.get("domainCategory") or "general"),
    )
    tf_imp = target_fit_improvement(tf_signals.required_terms_missing, lang)
    target_fit_task = {"target_fit": float(fit_score)}
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
        "targetRoleDomain": _domain_block(domain_target),
        "resumeDomain": _domain_block(domain_resume),
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
        "career_sw": career_sw,
        "tf_imp": tf_imp,
        "target_fit_extra": target_fit_extra,
        "target_fit_task": target_fit_task,
        "target_fit_bundle_extra": target_fit_bundle_extra,
    }
