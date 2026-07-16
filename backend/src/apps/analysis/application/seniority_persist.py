"""
Persisted seniority labels (rule / review / final) and evidence snapshots for audit + ML export.

See docs/analysis/tcc_gold_pipeline.md and seniority_policy.md.
"""
from __future__ import annotations

from typing import Any

from .inference.tasks.seniority.constants import SENIORITY_POLICY_VERSION
from .inference.signals.types import ResumeSignals
VALID_SENIORITY_LABELS = frozenset({"intern", "junior", "mid", "senior"})
VALID_LABEL_SOURCES = frozenset({"rule", "review"})
VALID_CONFIDENCE = frozenset({"low", "medium", "high"})
SENIORITY_LABEL_TO_SCORE = {"intern": 25, "junior": 50, "mid": 75, "senior": 100}


def signals_snapshot(rs: ResumeSignals) -> dict[str, Any]:
    """Structured signals used by policy (no PII)."""
    return {
        "total_months_experience": rs.total_months_experience,
        "effective_months_experience": rs.effective_months_experience,
        "experiences_count": rs.experiences_count,
        "bullets_count": rs.bullets_count,
        "has_current_role": rs.has_current_role,
        "months_in_current_role": rs.months_in_current_role,
        "has_internship_terms": rs.has_internship_terms,
        "has_leadership_terms": rs.has_leadership_terms,
        "word_count": rs.word_count,
        "completeness_score": rs.completeness_score,
        "completeness_level": rs.completeness_level,
        "insufficient_data": rs.insufficient_data,
        "reasons": list(rs.reasons)[:24],
    }


def build_seniority_evidence_json(
    rs: ResumeSignals,
    evidence_chain: list[dict[str, Any]],
    *,
    max_evidence: int = 24,
) -> dict[str, Any]:
    return {
        "policy_version": SENIORITY_POLICY_VERSION,
        "signals": signals_snapshot(rs),
        "evidence": list(evidence_chain)[:max_evidence],
    }


def normalize_seniority_label(raw: str | None) -> str | None:
    s = (raw or "").strip().lower()
    return s if s in VALID_SENIORITY_LABELS else None
