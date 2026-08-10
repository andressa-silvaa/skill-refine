"""
Sanitized resume/job text for neural inference (no PII in model input).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}(?:[\s.-]?\d{2,4})?",
    re.I,
)
URL_RE = re.compile(r"\bhttps?://[^\s]+|www\.[^\s]+", re.I)
CPF_LIKE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")


def _strip_pii(text: str) -> str:
    t = EMAIL_RE.sub(" ", text or "")
    t = URL_RE.sub(" ", t)
    t = PHONE_RE.sub(" ", t)
    t = CPF_LIKE.sub(" ", t)
    return t


def _clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _duration_months(exp: dict[str, Any]) -> int:
    def ym(value: Any) -> tuple[int, int] | None:
        parts = str(value or "").strip().split("-")
        if len(parts) >= 2:
            try:
                return int(parts[0]), int(parts[1])
            except ValueError:
                return None
        return None

    start = ym(exp.get("startDate"))
    if not start:
        return 0
    today = date.today()
    end = (
        (today.year, today.month)
        if exp.get("isCurrent") or not exp.get("endDate")
        else ym(exp.get("endDate"))
    )
    if not end:
        return 0
    return max(0, (end[0] - start[0]) * 12 + (end[1] - start[1]) + 1)


def resume_to_text_sanitized(resume_data: dict[str, Any], *, max_chars: int = 4000) -> str:
    """
    Build the sanitized string a model reads: summary, target role, then each experience with its
    duration and its achievement bullets, plus education and skills. Strips PII; truncates.

    Bullets and tenure were originally left out, so every neural task saw only titles and skills —
    the evidence that decides seniority and quality never reached the model. Duration is expressed
    in months rather than raw dates because PHONE_RE would eat date-like digit runs.

    Experiences stay in payload order (most recent first) so that truncation drops the least
    decision-relevant content.
    """
    data = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else {}
    parts: list[str] = []

    summary = str(data.get("summary") or "").strip()
    if summary:
        parts.append(summary)

    tp = str(data.get("targetPosition") or "").strip()
    if tp:
        parts.append(tp)

    experiences = data.get("experiences") or []
    if isinstance(experiences, list):
        for exp in experiences[:12]:
            if not isinstance(exp, dict):
                continue
            title = str(exp.get("position") or exp.get("title") or "").strip()
            months = _duration_months(exp)
            header = title
            if months:
                header = f"{title} ({months} meses)" if title else f"({months} meses)"
            if exp.get("isCurrent"):
                header = f"{header} (atual)".strip()
            if header:
                parts.append(header)
            for bullet in (exp.get("description") or [])[:10]:
                text = str(bullet).strip()
                if text:
                    parts.append(f"- {text}")

    education = data.get("educations") or data.get("education") or []
    if isinstance(education, list):
        for ed in education[:6]:
            if not isinstance(ed, dict):
                continue
            course = str(ed.get("course") or ed.get("degree") or "").strip()
            if course:
                parts.append(course)

    skills = data.get("skills") or []
    if isinstance(skills, list):
        skill_names: list[str] = []
        for s in skills[:80]:
            if isinstance(s, dict):
                n = str(s.get("name") or "").strip()
                if n:
                    skill_names.append(n)
            elif isinstance(s, str) and s.strip():
                skill_names.append(s.strip())
        if skill_names:
            parts.append(", ".join(skill_names))

    raw = _clean_ws(" \n".join(parts))
    raw = _strip_pii(raw)
    raw = _clean_ws(raw)
    if max_chars > 0 and len(raw) > max_chars:
        raw = raw[:max_chars].rsplit(" ", 1)[0].strip()
    return raw


def job_text_sanitized(job_text: str, *, max_chars: int = 2000) -> str:
    """Strip PII-ish patterns from job description; truncate."""
    raw = _clean_ws(_strip_pii(job_text or ""))
    if max_chars > 0 and len(raw) > max_chars:
        raw = raw[:max_chars].rsplit(" ", 1)[0].strip()
    return raw
