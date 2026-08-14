"""
Quality predictor: HF regression/classification or heuristic-based score 0-100.
"""
from __future__ import annotations

from contextlib import nullcontext
import re
from typing import Any

from apps.analysis.application.inference.cascade import CascadeResult, run_cascade

from .bullet_flags import predict_bullet_flags

LINK_PATTERN = re.compile(r"linkedin\.com|github\.com|portfolio|\.me/", re.I)
METRICS_PATTERN = re.compile(r"\d+%|\d+\s*(?:anos?|years?|años?)|R\$\s*\d+|\$\d+|%\s*(?:de|of)", re.I)
ACTION_VERBS = {
    "pt": ["liderou", "implementou", "desenvolveu", "gerenciou", "coordenou", "criou", "aumentou", "reduziu"],
    "en": ["led", "implemented", "developed", "managed", "coordinated", "created", "increased", "reduced"],
    "es": ["lideró", "implementó", "desarrolló", "gestionó", "coordinó", "creó", "aumentó", "redujo"],
}
LEADERSHIP_WORDS = re.compile(
    r"l[ií]der|lead|mentoria|mentoring|mentorship|coordena|coordinat|gest[aã]o|gerenci|gerente|"
    r"manager|roadmap|stakeholder|supervis|jefe|jefa|responsable|encargad",
    re.I,
)
ARCHITECTURE_WORDS = re.compile(
    r"arquitet|architecture|microsservi|microservice|integra[cç][aã]o|integration|platform|plataforma|governan|observability|observabilidade",
    re.I,
)
TECH_KEYWORDS = re.compile(
    r"\b(python|django|fastapi|react|sql|api|apis|etl|cloud|aws|azure|gcp|cypress|docker|kubernetes|nlp|java|node|typescript|postgres|redis)\b",
    re.I,
)

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

DEFAULT_QUALITY_LEVEL_TO_SCORE = {
    "poor": 30,
    "ok": 55,
    "strong": 78,
    "good": 72,
    "excellent": 92,
}


def _lang_code(lang: str) -> str:
    return (lang or "pt").split("-")[0]


def _heuristic_flags(text: str, lang: str) -> dict[str, bool | int | float]:
    text_lower = (text or "").lower()
    lang_code = _lang_code(lang)
    verbs = ACTION_VERBS.get(lang_code, ACTION_VERBS["pt"])
    has_metrics = bool(METRICS_PATTERN.search(text_lower))
    has_links = bool(LINK_PATTERN.search(text_lower))
    action_count = sum(1 for v in verbs if v in text_lower)
    has_action_verbs = action_count > 0
    bullets = text_lower.count("- ")
    bullet_density = bullets / max(1, len(text_lower.split()))
    return {
        "has_metrics": has_metrics,
        "has_links": has_links,
        "has_action_verbs": has_action_verbs,
        "action_verbs_count": action_count,
        "bullet_density": bullet_density,
    }


def _heuristic_score(flags: dict[str, bool | int]) -> int:
    score = 30
    if flags.get("has_metrics"):
        score += 25
    if flags.get("has_links"):
        score += 20
    if flags.get("has_action_verbs"):
        score += 25
    if flags.get("action_verbs_count", 0) >= 3:
        score += 5
    if (flags.get("bullet_density") or 0) > 0.01:
        score += 5
    return min(100, score)


def _resolve_quality_score_from_label(label: str) -> int | None:
    label_norm = str(label or "").strip().lower()
    if not label_norm:
        return None
    if label_norm.startswith("label_"):
        label_norm = label_norm.split("_", 1)[-1]
    return DEFAULT_QUALITY_LEVEL_TO_SCORE.get(label_norm)


DIMENSION_KEYS = ("ats", "clarity")


def _dimension_to_score(value: float, calibration: dict[str, Any] | None) -> int:
    """
    Map a rubric dimension onto the 0-100 scale, using the range the teacher actually used.

    A naive 1-5 -> 0-100 map is wrong here and it shows on screen. The teacher never scores `clarity`
    or `ats` below 3, so that map floors those dimensions near 50 and a resume whose quality reads 42
    would publish an `ats` of 72 — three numbers that contradict each other.

    So the observed label range is recorded at export time and mapped onto the same endpoints the
    level head uses (`quality_level_to_score`), which puts every published number on one scale. This
    is a rescale, not a re-decision: it is monotone, so the model's ordering survives untouched, and
    like the level map it is declared product policy rather than a fitted quantity.
    """
    if not isinstance(calibration, dict):
        clamped = max(1.0, min(5.0, float(value)))
        return int(round((clamped - 1.0) / 4.0 * 100.0))

    low = float(calibration.get("observed_low", 1.0))
    high = float(calibration.get("observed_high", 5.0))
    score_low = float(calibration.get("score_low", 30.0))
    score_high = float(calibration.get("score_high", 78.0))
    if high <= low:
        return int(round(max(0.0, min(100.0, score_high))))
    position = (float(value) - low) / (high - low)
    scaled = score_low + max(0.0, min(1.0, position)) * (score_high - score_low)
    return int(round(max(0.0, min(100.0, scaled))))


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
            mapped = _resolve_quality_score_from_label(str(label))
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
        dimensions[key] = _dimension_to_score(
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
    flags = _heuristic_flags(resume_text, language)
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
                value=(_heuristic_score(flags), flags),
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
    return int(score if score is not None else _heuristic_score(flags)), flags
