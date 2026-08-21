"""
Seniority resolution: the text probe decides, the rule is the fallback labelled as such.

Extracted from ``orchestrator.py`` so that module reads as the pipeline it is. The encoder arrives as
a parameter rather than being fetched here, so the whole analysis resolves it once and the test
suite keeps a single patch point on ``orchestrator.get_embeddings_model``.
"""
from __future__ import annotations

from typing import Any
from .tasks.seniority import (
    SENIORITY_LABELS,
    apply_tenure_floor,
    clamp_seniority_vetoes,
    rule_based_seniority,
)
from .tasks.seniority.constants import SENIORITY_POLICY_VERSION
from .tasks.seniority.text import predict_text_seniority
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
    encoder: Any,
) -> dict[str, Any]:
    base_label, base_confidence, base_evidence = rule_based_seniority(rs)

    final_label, veto_evidence = clamp_seniority_vetoes(base_label, rs)
    seniority_confidence = base_confidence
    seniority_evidence = list(base_evidence) + list(veto_evidence)
    ml_status = "skipped_no_model"
    seniority_label_source = "rule_policy"
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

    sanitized_cv = resume_to_text_sanitized(resume_data)
    text_pred: dict[str, Any] = {"label": None, "confidence": "low", "probs": {}, "source": "none"}
    fuse_meta: dict[str, Any] = {}

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
            ml_status = "applied_text_seniority_probe"
            final_label, floor_evidence = apply_tenure_floor(final_label, resume_data)
            seniority_evidence.extend(floor_evidence)
            final_label, veto_evidence = clamp_seniority_vetoes(final_label, rs)
            seniority_evidence.extend(veto_evidence)
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
        logger.warning(
            "seniority answered by rule_policy: the text probe is unavailable",
            extra={
                "probe_enabled": bool(config.get("text_seniority_probe_enabled")),
                "encoder_loaded": encoder is not None,
            },
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
