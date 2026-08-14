"""
Quality predictor: the embedding probe decides, and refuses when it cannot.

The regex tables and the heuristic score live in ``heuristics.py``; the rubric rescale lives in
``dimensions.py``. Both are re-exported here because ``resume_signals.py``, the test suite and the
ml scripts import those names from this module.
"""
from __future__ import annotations

from contextlib import nullcontext
from typing import Any

from apps.analysis.application.inference.cascade import CascadeResult, run_cascade

from .bullet_flags import predict_bullet_flags
from .dimensions import DIMENSION_KEYS, dimension_to_score
from .heuristics import (
    ACTION_VERBS,
    DEFAULT_QUALITY_LEVEL_TO_SCORE,
    LEADERSHIP_WORDS,
    LINK_PATTERN,
    METRICS_PATTERN,
    heuristic_flags,
    heuristic_score,
    lang_code,
    resolve_quality_score_from_label,
)

__all__ = [
    "ACTION_VERBS",
    "DEFAULT_QUALITY_LEVEL_TO_SCORE",
    "DIMENSION_KEYS",
    "LEADERSHIP_WORDS",
    "LINK_PATTERN",
    "LOW_CONFIDENCE_MARGIN",
    "METRICS_PATTERN",
    "predict_quality",
    "predict_quality_detailed",
]

# Below this margin between the head's top two classes, the quality score is published but marked
# low confidence. The value is the 10% operating point of the measured risk-coverage curve
# (ml/reports/completeness_caps_v3.md): withholding confidence from the lowest-margin 10% of resumes
# takes accuracy on the rest from 92.9% to 96.5%, removing 27 of 49 errors. 15% would reach 97.4%
# and 30% only 98.8%, so the return flattens right after this point. Where the knee sits is measured;
# choosing to sit on it is declared product policy.
#
# This does NOT replace the completeness caps, and the two are not interchangeable. A completely
# empty resume scores 78 with a *confident* margin of 0.368, because an all-zero feature vector lands
# on the linear head's bias term. That is an out-of-distribution failure, invisible to any
# uncertainty measure, and the completeness cap is what catches it.
LOW_CONFIDENCE_MARGIN = 0.158



def _predict_probe_quality(
    bundle: dict[str, Any],
    encoder: Any,
    resume_text: str,
    resume_data: dict[str, Any],
) -> tuple[int, dict[str, int], float] | None:
    """
    Score the level head, then each rubric dimension head that the bundle carries.

    The level head decides the headline number, because its label (``quality_target``) exists on every
    generated resume and was confirmed by human review. The dimension heads are trained on the LLM
    teacher's 1-5 rubric and exist only to give ``ats`` and ``clarity`` their own answer instead of a
    copy of the headline.

    Also returns the **margin** between the top two class probabilities. Measured over 691 labelled
    resumes, that margin ranks a correct prediction above an incorrect one with AUC 0.880, against
    0.872 for the raw top probability and 0.805 for entropy — the same ordering section 6 found for
    domain retrieval, where a margin separated what an absolute score could not.
    """
    from apps.analysis.application.inference.text_probe import encode_for_bundle

    heads = bundle.get("heads") or {}
    level_head = heads.get("level")
    if level_head is None:
        return None
    matrix = encode_for_bundle(bundle, encoder, resume_text, resume_data)
    metadata = bundle.get("_metadata") if isinstance(bundle.get("_metadata"), dict) else {}
    score_map = metadata.get("quality_level_to_score") or DEFAULT_QUALITY_LEVEL_TO_SCORE

    probabilities = level_head.predict_proba(matrix)[0]
    total = 0.0
    weight = 0.0
    for label, probability in zip(list(level_head.classes_), probabilities):
        mapped = score_map.get(str(label))
        if mapped is None:
            mapped = resolve_quality_score_from_label(str(label))
        if mapped is not None:
            total += float(probability) * float(mapped)
            weight += float(probability)
    if weight <= 0:
        return None
    score = int(round(min(100, max(0, total / weight))))

    calibration = metadata.get("dimension_calibration")
    calibration = calibration if isinstance(calibration, dict) else {}
    dimensions: dict[str, int] = {}
    for key in (*DIMENSION_KEYS, "impact"):
        head = heads.get(key)
        if head is None:
            continue
        dimensions[key] = dimension_to_score(
            float(head.predict(matrix)[0]), calibration.get(key)
        )
    ordered = sorted((float(p) for p in probabilities), reverse=True)
    margin = float(ordered[0] - ordered[1]) if len(ordered) > 1 else float(ordered[0])
    return score, dimensions, margin


def predict_quality_detailed(
    resume_text: str,
    language: str,
    sections: Any,
    seniority_hint: str | None = None,
    quality_bundle: tuple[Any, dict] | None = None,
    *,
    neural_allowed: bool = True,
    probe_bundle: dict[str, Any] | None = None,
    embeddings_model: Any = None,
    resume_data: dict[str, Any] | None = None,
    allow_heuristic_answer: bool = False,
    bullet_bundle: dict[str, Any] | None = None,
    bullet_detail: dict[str, Any] | None = None,
) -> tuple[int | None, dict[str, bool | int], dict[str, Any]]:
    """
    Predict quality score 0-100, feature flags, and the per-dimension block.

    Two steps only: the embedding probe, then a refusal. The heuristic no longer decides.

    ``_heuristic_score`` averages 41.4 / 52.4 / 57.8 on resumes planted as poor / fair / good — it is
    nearly flat on the axis it claims to measure, while carrying 78% of the final score. Serving that
    as a fallback does not give the user an answer, it gives them a number indistinguishable from a
    model's. So when the probe cannot answer, the score is ``None`` and the caller decides what to do.

    ``allow_heuristic_answer`` exists for the golden snapshot suite, which freezes the old behaviour so
    the fallback code stays correct even though it no longer serves users. The flags are always
    returned regardless, because ``derive_insights`` reads them to choose which strengths and
    improvements to show — that is a separate, still-heuristic decision (handoff 7.1 group A).
    """
    flags = heuristic_flags(resume_text, language)
    if bullet_detail is None:
        bullet_detail = predict_bullet_flags(bullet_bundle, embeddings_model, resume_data)
    flags_provider = "heuristics"
    if bullet_detail is not None:
        flags.update(bullet_detail["flags"])
        flags_provider = "bullet_probe"

    def _step_probe() -> CascadeResult:
        if not neural_allowed or not probe_bundle or embeddings_model is None or resume_data is None:
            return CascadeResult(value=None, provider="quality_probe", status="skipped")
        predicted = _predict_probe_quality(probe_bundle, embeddings_model, resume_text, resume_data)
        if predicted is None:
            return CascadeResult(value=None, provider="quality_probe", status="error")
        score, dimensions, margin = predicted
        return CascadeResult(
            value=(score, flags),
            provider="quality_probe",
            status="applied",
            extra={"dimensions": dimensions, "margin": margin},
        )

    def _terminal() -> CascadeResult:
        if not allow_heuristic_answer and not neural_allowed:
            # Distinct from a missing bundle, and the operator must not be sent looking for one.
            # The probe was never consulted: completeness read `insufficient`, and the orchestrator
            # gates the neural path off for that level. Refusing is the intended outcome; blaming
            # the artefact is not.
            return CascadeResult(
                value=(None, flags),
                provider="no_model",
                status="applied",
                extra={
                    "reason": "resume too incomplete to score: completeness is 'insufficient', so "
                    "the quality probe was not consulted. This is not a missing bundle."
                },
            )
        if allow_heuristic_answer:
            return CascadeResult(
                value=(heuristic_score(flags), flags),
                provider="heuristics",
                status="applied",
            )
        return CascadeResult(
            value=(None, flags),
            provider="no_model",
            status="applied",
            extra={"reason": "quality probe unavailable and the heuristic is not allowed to answer"},
        )

    result = run_cascade([_step_probe], default=_terminal())
    score, resolved_flags = result.value
    detail: dict[str, Any] = {"provider": result.provider, "flags_provider": flags_provider}
    if bullet_detail is not None:
        detail["bullets"] = {
            "count": bullet_detail["bullet_count"],
            "positives": bullet_detail["counts"],
        }
    if isinstance(result.extra, dict):
        dimensions = result.extra.get("dimensions")
        if isinstance(dimensions, dict) and dimensions:
            detail["dimensions"] = dimensions
        margin = result.extra.get("margin")
        if isinstance(margin, (int, float)):
            detail["margin"] = float(margin)
            detail["confidence"] = "high" if float(margin) >= LOW_CONFIDENCE_MARGIN else "low"
        reason = result.extra.get("reason")
        if reason:
            detail["reason"] = str(reason)
    return score, resolved_flags, detail


def predict_quality(
    resume_text: str,
    language: str,
    sections: Any,
    seniority_hint: str | None = None,
    quality_bundle: tuple[Any, dict] | None = None,
    *,
    neural_allowed: bool = True,
    probe_bundle: dict[str, Any] | None = None,
    embeddings_model: Any = None,
    resume_data: dict[str, Any] | None = None,
    allow_heuristic_answer: bool = True,
) -> tuple[int, dict[str, bool | int]]:
    """
    Score and flags only; see ``predict_quality_detailed`` for the provider and the reason.

    Defaults to allowing the heuristic answer so that callers holding a plain ``(score, flags)``
    contract keep a number to work with. Production goes through ``predict_quality_detailed``, which
    defaults the other way.
    """
    score, flags, _detail = predict_quality_detailed(
        resume_text,
        language,
        sections,
        seniority_hint,
        quality_bundle,
        neural_allowed=neural_allowed,
        probe_bundle=probe_bundle,
        embeddings_model=embeddings_model,
        resume_data=resume_data,
        allow_heuristic_answer=allow_heuristic_answer,
    )
    return int(score if score is not None else heuristic_score(flags)), flags
