"""
Fixed feature vector for target-fit sklearn model (training + serving).

Must stay in sync with ``ml/training/src/train_target_fit.py`` row builder.
"""
from __future__ import annotations

from typing import Any

from .domain_inference import DOMAIN_CATEGORIES
from .fit_signals import TargetFitSignals


def _one_hot(domain: str, categories: tuple[str, ...]) -> list[float]:
    d = (domain or "general").strip().lower()
    if d not in categories:
        d = "general"
    return [1.0 if c == d else 0.0 for c in categories]


def _domain_mismatch(resume_domain: str, target_domain: str) -> float:
    rd = (resume_domain or "").strip().lower()
    td = (target_domain or "").strip().lower()
    if not rd or not td or rd == "general" or td == "general":
        return 0.0
    return 1.0 if rd != td else 0.0


def _edu_bits(alignment: str) -> tuple[float, float, float]:
    a = (alignment or "weak").strip().lower()
    if a == "strong":
        return 0.0, 0.0, 1.0
    if a == "medium":
        return 0.0, 1.0, 0.0
    return 1.0, 0.0, 0.0


def target_fit_feature_names() -> list[str]:
    names: list[str] = [
        "required_terms_hit",
        "required_terms_total",
        "skills_hit",
        "skills_total",
        "experience_keyword_hits",
        "completeness_score",
        "edu_weak",
        "edu_medium",
        "edu_strong",
        "portfolio_evidence",
        "domain_mismatch",
        "has_job_text",
    ]
    for c in DOMAIN_CATEGORIES:
        names.append(f"target_domain_{c}")
    for c in DOMAIN_CATEGORIES:
        names.append(f"resume_domain_{c}")
    return names


def signals_dict_from_dataclass(sig: TargetFitSignals) -> dict[str, Any]:
    return {
        "required_terms_hit": int(sig.required_terms_hit),
        "required_terms_total": int(sig.required_terms_total),
        "skills_hit": int(sig.skills_hit),
        "skills_total": int(sig.skills_total),
        "experience_keyword_hits": int(sig.experience_keyword_hits),
        "education_alignment": str(sig.education_alignment or "weak"),
        "portfolio_evidence": bool(sig.portfolio_evidence),
        "completeness_score": int(sig.completeness_score or 0),
    }


def target_fit_feature_row(
    signals: TargetFitSignals | dict[str, Any],
    *,
    resume_domain: str,
    target_domain: str,
    has_job_text: bool,
) -> list[float]:
    if isinstance(signals, TargetFitSignals):
        s = signals_dict_from_dataclass(signals)
    else:
        s = dict(signals)
    ew, em, es = _edu_bits(str(s.get("education_alignment") or "weak"))
    row: list[float] = [
        float(s.get("required_terms_hit") or 0),
        float(max(0, int(s.get("required_terms_total") or 0))),
        float(s.get("skills_hit") or 0),
        float(max(0, int(s.get("skills_total") or 0))),
        float(s.get("experience_keyword_hits") or 0),
        float(max(0, min(100, int(s.get("completeness_score") or 0)))),
        ew,
        em,
        es,
        1.0 if s.get("portfolio_evidence") else 0.0,
        _domain_mismatch(resume_domain, target_domain),
        1.0 if has_job_text else 0.0,
    ]
    row.extend(_one_hot(target_domain, DOMAIN_CATEGORIES))
    row.extend(_one_hot(resume_domain, DOMAIN_CATEGORIES))
    return row


def target_fit_feature_row_from_jsonl(
    row: dict[str, Any],
) -> list[float]:
    """Build the same vector from a dataset JSONL row."""
    sig = row.get("signals") or {}
    return target_fit_feature_row(
        sig,
        resume_domain=str(row.get("resume_domain_category") or "general"),
        target_domain=str(row.get("domain_category") or "general"),
        has_job_text=bool(row.get("has_job_description")),
    )
