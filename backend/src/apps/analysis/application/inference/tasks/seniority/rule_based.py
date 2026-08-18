"""
Structural seniority policy (primary signal). See docs/analysis/seniority_policy.md.
"""
from __future__ import annotations

from typing import Any

from ...signals.types import ResumeSignals

_ORDER = ("intern", "junior", "mid", "senior")


def _confidence_from_signals(signals: ResumeSignals, base: str) -> str:
    if signals.insufficient_data:
        return "low"
    date_noise = sum(1 for r in signals.reasons if r.startswith("experience_") and "invalid" in r)
    if date_noise >= 2:
        return "low"
    if signals.experiences_count >= 2 and signals.total_months_experience > 0 and not signals.insufficient_data:
        if base in ("mid", "senior"):
            return "high"
        return "medium"
    if signals.experiences_count == 1 and signals.total_months_experience >= 12:
        return "medium"
    return "low"


def rule_based_seniority(signals: ResumeSignals) -> tuple[str, str, list[dict[str, Any]]]:
    """
    Returns (label, confidence, evidence) with confidence in low|medium|high.
    """
    evidence: list[dict[str, Any]] = []

    if signals.experiences_count == 0:
        evidence.append(
            {"type": "veto", "rule": "no_structured_experience", "section": "experience", "count": 0}
        )
        return "junior", "low", evidence

    if signals.has_internship_terms and signals.effective_months_experience < 24:
        evidence.append(
            {
                "type": "structural",
                "rule": "internship_terms_detected",
                "months": signals.effective_months_experience,
            }
        )
        return "intern", "medium", evidence

    m = signals.effective_months_experience
    if m < 12:
        evidence.append({"type": "structural", "rule": "total_months_lt_12", "months": m})
        return "intern", "medium", evidence

    if m <= 24:
        evidence.append({"type": "structural", "rule": "total_months_12_24", "months": m})
        return "junior", _confidence_from_signals(signals, "junior"), evidence

    if m <= 60:
        evidence.append({"type": "structural", "rule": "total_months_25_60", "months": m})
        return "mid", _confidence_from_signals(signals, "mid"), evidence

    if signals.experiences_count >= 2 and signals.bullets_count >= 6:
        evidence.append({"type": "structural", "rule": "senior_track", "months": m})
        return "senior", _confidence_from_signals(signals, "senior"), evidence

    evidence.append({"type": "structural", "rule": "senior_months_insufficient_evidence", "months": m})
    return "mid", "medium", evidence


def apply_tenure_floor(
    label: str,
    resume_data: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    """
    Nunca rotular abaixo do que o tempo de casa documentado sustenta.

    Simetria dos vetos abaixo, que só sabem descer. Existe porque a sonda de texto é **só-texto por
    decisão de projeto** — ler os meses vale 1,6 ponto para ela (§9.3) — e em currículo escrito fora
    do estilo do corpus ela subestima num sentido só: em 19 currículos escritos à mão saiu mais baixa
    que a regra 12 vezes e mais alta zero, com "intern" em carreiras de 9 a 12 anos
    (ml/reports/length_leak_v3.md registra o que a investigação descartou).

    Não conserta o modelo, e não finge consertar: é segurança sobre evidência **presente**, do mesmo
    tipo declarado que ``clamp_seniority_vetoes`` é sobre evidência ausente. Um currículo com 111
    meses de experiência datada não sai júnior, qualquer que seja a leitura da prosa.
    """
    from ...resume_signals import structured_seniority_floor_lift

    floor = structured_seniority_floor_lift(resume_data)
    if not floor:
        return label, []
    try:
        current, minimum = _ORDER.index(label), _ORDER.index(floor)
    except ValueError:
        return label, []
    if current >= minimum:
        return label, []
    return floor, [
        {
            "type": "floor",
            "rule": "never_below_documented_tenure",
            "from": label,
            "to": floor,
        }
    ]


def clamp_seniority_vetoes(
    label: str,
    signals: ResumeSignals,
    *,
    min_bullets: int = 6,
) -> tuple[str, list[dict[str, Any]]]:
    """Post-ML vetoes: never senior without evidence; never mid/senior on low real tenure."""
    extra: list[dict[str, Any]] = []
    if label == "senior":
        if signals.experiences_count == 0:
            extra.append({"type": "veto", "rule": "never_senior_without_experience"})
            return "junior", extra
        if signals.bullets_count < min_bullets:
            extra.append({"type": "veto", "rule": "never_senior_few_bullets", "count": signals.bullets_count})
            return "mid", extra
    if label in ("mid", "senior") and signals.total_months_experience < 24:
        capped = "junior" if signals.total_months_experience >= 12 else "intern"
        extra.append(
            {
                "type": "veto",
                "rule": "never_mid_or_above_on_low_tenure",
                "from": label,
                "to": capped,
                "total_months_experience": signals.total_months_experience,
            }
        )
        return capped, extra
    return label, extra
