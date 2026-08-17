"""
Seniority resolution: the text probe decides, the rule degrades labelled, and the blend stays off.

Extracted from ``orchestrator.py`` so that module reads as the pipeline it is. The encoder arrives as
a parameter rather than being fetched here, so the whole analysis resolves it once and the test
suite keeps a single patch point on ``orchestrator.get_embeddings_model``.
"""
from __future__ import annotations

from django.conf import settings
from typing import Any
from .cascade import CascadeResult, run_cascade
from .config import get_signals_ml_thresholds
from .loader import get_model_bundle
from .loader_signals_model import get_signals_ml_bundle, signals_ml_metadata_for_extra
from .tasks.seniority import (
    SENIORITY_LABELS,
    apply_tenure_floor,
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
from .tasks.seniority.text.loader_seniority_probe import get_seniority_probe_bundle
from .text_probe import probe_metadata_for_task
from .text_sanitizer import resume_to_text_sanitized

import logging

logger = logging.getLogger(__name__)

SENIORITY_TO_SCORE = {"intern": 25, "junior": 50, "mid": 75, "senior": 100}

def _resolve_seniority(
    *,
    resume_data: dict[str, Any],
    resume_text: str,
    lang: str,
    config: dict[str, Any],
    rs: Any,
    allow_ml_seniority: bool,
    encoder: Any,
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
            fl, veto_ev = clamp_seniority_vetoes(
                ml_lab, rs, min_bullets=int(sm_cfg.get("SIGNALS_ML_SENIOR_MIN_BULLETS", 6))
            )
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

    probe_bundle = get_seniority_probe_bundle(config)

    if probe_bundle is not None and encoder is not None:
        # The probe decides. Blending it back into the rule was measured and it loses to both
        # components — see ml/reports/seniority_fusion_v3.md — so the rule stays behind it as the
        # fallback rather than as a co-signer, and only the vetoes still touch the answer.
        text_pred = predict_text_seniority(
            sanitized_cv,
            lang,
            None,
            allow_lexical_fallback=False,
            probe_bundle=probe_bundle,
            embeddings_model=encoder,
            resume_data=resume_data,
        )
        probe_label = text_pred.get("label")
        if probe_label:
            final_label = str(probe_label)
            seniority_confidence = str(text_pred.get("confidence") or "low")
            seniority_label_source = "text_seniority_probe"
            # Piso antes dos vetos: o piso levanta com base em evidencia presente, os vetos descem
            # com base em evidencia ausente, e a seguranca precisa ter a ultima palavra.
            final_label, floor_evidence = apply_tenure_floor(final_label, resume_data)
            seniority_evidence.extend(floor_evidence)
            final_label, veto_evidence = clamp_seniority_vetoes(final_label, rs)
            seniority_evidence.extend(veto_evidence)
            # Quem mudou o rotulo assina. Manter `text_seniority_probe` quando uma regra trocou a
            # resposta atribuiria ao modelo uma decisao que nao foi dele — e nos 20 curriculos
            # escritos a mao o piso trocou 12, ou seja a atribuicao erraria na maioria deles.
            if floor_evidence or veto_evidence:
                marks = ["floor"] if floor_evidence else []
                marks += ["veto"] if veto_evidence else []
                seniority_label_source = "probe+" + "+".join(marks)
            seniority_evidence.append(
                {
                    "type": "text_seniority",
                    "label": probe_label,
                    "confidence": text_pred.get("confidence"),
                    "source": text_pred.get("source"),
                }
            )
            model_bundle = (
                None,
                {
                    "labels": list(SENIORITY_LABELS),
                    **probe_metadata_for_task(probe_bundle, provider="text_seniority_probe"),
                },
            )
    elif config.get("require_model_answer", True):
        seniority_label_source = "rule_policy"
        logger.warning(
            "seniority answered by rule_policy: the text probe is unavailable",
            extra={
                "probe_enabled": bool(config.get("text_seniority_probe_enabled")),
                "encoder_loaded": encoder is not None,
            },
        )
    elif config["text_seniority_fusion_enabled"]:
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
