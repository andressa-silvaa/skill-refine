"""
Structured resume signals for analysis (feature engineering, no ML).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResumeSignals:
    """Deterministic signals extracted from structured payload + section text."""

    total_months_experience: int
    effective_months_experience: int
    experiences_count: int
    bullets_count: int
    has_current_role: bool
    months_in_current_role: int
    has_internship_terms: bool
    has_leadership_terms: bool
    has_links: bool
    summary_char_count: int
    skills_count: int
    education_present: bool
    completeness_score: int
    completeness_level: str
    insufficient_data: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    word_count: int = 0
    language: str = "pt-BR"
