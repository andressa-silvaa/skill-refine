"""
Seniority predictor: HF (SequenceClassification) softmax-gap for ML adjust gating.
"""
from __future__ import annotations

from typing import Any

SENIORITY_LABELS = ("intern", "junior", "mid", "senior")


def predict_hf_seniority_probs(
    resume_text: str,
    language: str,
    model_bundle: tuple[Any, Any] | None,
    *,
    allow: bool = True,
) -> tuple[str | None, float, str]:
    """
    HF softmax gap (top1 - top2) for ML adjust gating. Skips TF-IDF / heuristics.
    Returns (label_or_none, gap_0_1, provider_tag).
    """
    if not allow or not model_bundle:
        return (None, 0.0, "skipped")
    model_or_pipeline, extra = model_bundle
    if model_or_pipeline is None:
        return (None, 0.0, "no_model")
    if not isinstance(extra, dict) or extra.get("tokenizer") is None:
        return (None, 0.0, "non_hf")
    tokenizer = extra["tokenizer"]
    max_length = 512
    if isinstance(extra.get("metadata"), dict):
        limits = extra["metadata"].get("input_limits") or {}
        max_length = limits.get("max_tokens", 512)
    try:
        import torch

        inputs = tokenizer(
            resume_text[:12000],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        ctx = getattr(torch, "inference_mode", None)
        infer_ctx = ctx() if callable(ctx) else torch.no_grad()
        with infer_ctx:
            out = model_or_pipeline(**inputs)
        probs = torch.nn.functional.softmax(out.logits, dim=-1).squeeze(0)
        top2 = torch.topk(probs, k=min(2, probs.numel()))
        if top2.values.numel() < 2:
            gap = 1.0
        else:
            gap = (top2.values[0] - top2.values[1]).item()
        pred_id = int(top2.indices[0])
        if 0 <= pred_id < len(SENIORITY_LABELS):
            return (SENIORITY_LABELS[pred_id], float(gap), "hf")
    except Exception:
        pass
    return (None, 0.0, "hf_error")
