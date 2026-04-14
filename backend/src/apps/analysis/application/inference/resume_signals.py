"""
Deterministic resume signals for gating insights and caps (no ML).
Uses structured payload: targetPosition, experiences, educations, skills, summary.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

# Cargo alvo / carreira em tecnologia (pt/en/es hints)
_TECH_ROLE_RE = re.compile(
    r"programador|programadora|developer|desenvolvedor|desenvolvedora|software|"
    r"\bdevops\b|backend|front\s*[-]?end|full\s*[-]?stack|dados|data\s*science|"
    r"cientista\s+de\s+dados|engenheir[oa]?\s+de\s+software|engenheir[oa]?\s+de\s+dados|"
    r"analista\s+de\s+sistemas|analista\s+de\s+dados|sistemas\s+de\s+informa|"
    r"ti\b|i\.t\.|tecnolog|computa\w*|dev\s|"
    r"web\s+developer|mobile|android|ios|cloud|cyber|seguran\w*\s+da\s+informa",
    re.I,
)

# Formação claramente de TI / STEM útil para dev
_TECH_EDU_RE = re.compile(
    r"computa\w*|inform[aá]tica|software|sistemas\s+de\s+informa|ci[eê]ncia[s]?\s+da\s+computa|"
    r"engenharia\s+de\s+software|engenharia\s+da\s+computa|engenharia\s+el[eé]trica|"
    r"engenharia\s+mecatr|an[aá]lise\s+e\s+desenvolvimento|ads\b|t[eé]cnico\s+em\s+inform[aá]tica|"
    r"computer\s+science|software\s+engineering|data\s+science|machine\s+learning|"
    r"matem[aá]tica|estat[ií]stica|f[ií]sica|ciberseguran|redes\s+de\s+comput",
    re.I,
)

# Cursos tipicamente fora de TI (quando o alvo é tech)
_NON_TECH_EDU_RE = re.compile(
    r"biologia|biological|biomedic|medicina|enfermagem|direito|letras|"
    r"hist[oó]ria|geografia|pedagogia|psicologia|nutri\w*|jornalismo|"
    r"marketing|contabil|administra|arquitetura\s+e\s+urbanismo|"
    r"veterin[aá]ria|odontologia|farm[aá]cia",
    re.I,
)

# Limites de palavra: evita "intern" em "interno", "internal", "desenvolvimento" (falso estágio).
_INTERN_TITLE_RE = re.compile(
    r"\best[aá]gio\b|\bestagi[aá]ri[oa]?\b|\binternship\b|\bintern\b|\btrainee\b",
    re.I,
)

_STUDENT_RE = re.compile(
    r"\bestudante\b|\bstudent\b|\balun[oa]\b",
    re.I,
)

# Anos explícitos só em campos de carreira (evita "curso de 2 anos" em formação).
# Aceita "2+ anos", "5 + anos" (comum em resumos tipo LinkedIn).
_WORK_YEARS_PATTERN = re.compile(r"(\d+)\s*\+\s*(?:anos?|years?|años?)|(\d+)\s+(?:anos?|years?|años?)", re.I)
_PT_WORD_TO_INT = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "três": 3,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
}
_PT_WORD_YEARS_PATTERN = re.compile(
    r"\b(um|uma|dois|duas|tr[eê]s|tres|quatro|cinco|seis|sete|oito|nove|dez)\s+anos?\b",
    re.I,
)

_JUNIOR_TITLE_HINT = re.compile(r"j[úu]nior|junior|\bjr\.?\b", re.I)


def _parse_payload_date(value: str | None) -> date | None:
    """YYYY-MM-DD ou YYYY-MM (dia 1), alinhado ao payload da API de currículos."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    parts = raw.split("-")
    try:
        if len(parts) == 3:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            return date(y, m, d)
        if len(parts) == 2:
            y, m = int(parts[0]), int(parts[1])
            if m < 1 or m > 12:
                return None
            return date(y, m, 1)
    except (ValueError, TypeError):
        return None
    return None


def _experience_span_months(exp: dict[str, Any]) -> int | None:
    start = _parse_payload_date(str(exp.get("startDate") or "").strip() or None)
    if not start:
        return None
    is_current = bool(exp.get("isCurrent"))
    end_raw = str(exp.get("endDate") or "").strip()
    if is_current:
        end = date.today()
    else:
        end = _parse_payload_date(end_raw) if end_raw else None
    if not end or end < start:
        return None
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def max_experience_tenure_months(resume_data: dict[str, Any]) -> int:
    """Maior tempo (meses) num único cargo, a partir de datas estruturadas."""
    best = 0
    for exp in _data(resume_data).get("experiences") or []:
        span = _experience_span_months(exp)
        if span is not None:
            best = max(best, span)
    return best


def max_years_mentioned_in_work_context(resume_data: dict[str, Any]) -> int:
    """Maior número N em 'N anos' em nome do CV, alvo, resumo e experiências."""
    data = _data(resume_data)
    parts: list[str] = []
    parts.append(str(resume_data.get("name") or ""))
    for key in ("targetPosition", "summary"):
        parts.append(str(data.get(key) or ""))
    for exp in data.get("experiences") or []:
        parts.append(str(exp.get("position") or ""))
        parts.append(str(exp.get("company") or ""))
        for b in exp.get("description") or []:
            parts.append(str(b))
    blob = " ".join(parts).lower()
    hits: list[int] = []
    for m in _WORK_YEARS_PATTERN.finditer(blob):
        g1, g2 = m.group(1), m.group(2)
        if g1:
            hits.append(int(g1))
        elif g2:
            hits.append(int(g2))
    for m in _PT_WORD_YEARS_PATTERN.finditer(blob):
        w = m.group(1).lower().replace("ê", "e")
        if w in _PT_WORD_TO_INT:
            hits.append(_PT_WORD_TO_INT[w])
    return max(hits) if hits else 0


def has_junior_title_hint(resume_data: dict[str, Any]) -> bool:
    data = _data(resume_data)
    for blob in (
        str(resume_data.get("name") or ""),
        str(data.get("targetPosition") or ""),
        str(data.get("summary") or ""),
    ):
        if _JUNIOR_TITLE_HINT.search(blob.lower()):
            return True
    for exp in data.get("experiences") or []:
        if _JUNIOR_TITLE_HINT.search((exp.get("position") or "").lower()):
            return True
    return False


def has_internship_position(resume_data: dict[str, Any]) -> bool:
    return any(
        bool((e.get("position") or "").strip() and _INTERN_TITLE_RE.search((e.get("position") or "").strip()))
        for e in _data(resume_data).get("experiences") or []
    )


def structured_seniority_floor_lift(resume_data: dict[str, Any]) -> str | None:
    """
    Piso mínimo plausível (sem ML) para não rotular como estágio quem já tem trajetória júnior.
    None = não forçar alteração em relação ao modelo/heurística.
    """
    if has_internship_position(resume_data):
        return None
    tenure_m = max_experience_tenure_months(resume_data)
    work_y = max_years_mentioned_in_work_context(resume_data)
    if tenure_m >= 60 or work_y >= 7:
        return "senior"
    if tenure_m >= 36 or work_y >= 4:
        return "mid"
    if tenure_m >= 14 or work_y >= 2:
        return "junior"
    if has_junior_title_hint(resume_data) and (tenure_m >= 10 or work_y >= 1):
        return "junior"
    return None


_TECH_SKILL_RE = re.compile(
    r"\b(python|java|javascript|typescript|react|node|sql|django|flask|fastapi|"
    r"angular|vue|kotlin|swift|go\b|rust|c\+\+|\.net|aws|azure|docker|kubernetes|git)\b",
    re.I,
)


def _data(resume_data: dict[str, Any]) -> dict[str, Any]:
    return resume_data.get("data", resume_data)


def experience_bullet_count(resume_data: dict[str, Any]) -> int:
    n = 0
    for exp in _data(resume_data).get("experiences") or []:
        for b in exp.get("description") or []:
            if str(b).strip():
                n += 1
    return n


def _shallow_single_experience_block(exp: dict[str, Any]) -> bool:
    """
    Pouquíssimo conteúdo na única experiência (ex.: cargo alvo no campo posição + 1 bullet curto),
    sem precisar da palavra 'estágio' no título.
    """
    bullets = [str(b).strip() for b in (exp.get("description") or []) if str(b).strip()]
    blob = " ".join(
        p
        for p in [
            str(exp.get("position") or "").strip(),
            str(exp.get("company") or "").strip(),
            *bullets,
        ]
        if p
    ).strip()
    if not blob:
        return True
    wc = len(blob.split())
    if not bullets:
        return wc <= 14 or len(blob) < 120
    if len(bullets) <= 2:
        return wc <= 52 or len(blob) < 400
    if len(bullets) == 3:
        return wc <= 40 and len(blob) < 320
    return False


def is_thin_student_or_intern_profile(resume_data: dict[str, Any]) -> bool:
    """
    Estágio curto / estudante / experiência única muito superficial — não deve virar pleno nem score alto.
    Não aplica a quem já tem carreira júnior mensurável (datas ou texto), sem cargo de estágio.
    """
    data = _data(resume_data)
    experiences: list[dict[str, Any]] = list(data.get("experiences") or [])
    intern_in_role = any(
        bool((e.get("position") or "").strip() and _INTERN_TITLE_RE.search((e.get("position") or "").strip()))
        for e in experiences
    )

    tenure_months = max_experience_tenure_months(resume_data)
    work_years = max_years_mentioned_in_work_context(resume_data)
    if not intern_in_role:
        if tenure_months >= 14:
            return False
        if work_years >= 2:
            return False
        if has_junior_title_hint(resume_data) and (tenure_months >= 10 or work_years >= 1):
            return False

    if len(experiences) > 1:
        return False

    bullets = experience_bullet_count(resume_data)
    if bullets > 3:
        return False

    summary = (data.get("summary") or "").strip().lower()
    student_like = bool(summary and _STUDENT_RE.search(summary))

    if intern_in_role or student_like:
        return True

    if len(experiences) == 1 and _shallow_single_experience_block(experiences[0]):
        return True

    return False


def _education_blob_lower(resume_data: dict[str, Any]) -> str:
    parts: list[str] = []
    for edu in _data(resume_data).get("educations") or []:
        for k in ("degree", "course", "institution"):
            parts.append(str(edu.get(k) or ""))
    return " ".join(parts).lower()


def _has_nonempty_education(resume_data: dict[str, Any]) -> bool:
    for edu in _data(resume_data).get("educations") or []:
        if any(str(edu.get(k) or "").strip() for k in ("degree", "course", "institution")):
            return True
    return False


def tech_target_context(resume_data: dict[str, Any]) -> str:
    data = _data(resume_data)
    target = data.get("targetPosition") or ""
    summary = data.get("summary") or ""
    return f"{target} {summary}".strip().lower()


def looks_like_tech_target(resume_data: dict[str, Any]) -> bool:
    return bool(_TECH_ROLE_RE.search(tech_target_context(resume_data)))


def education_aligned_with_target(resume_data: dict[str, Any]) -> bool:
    """
    Só elogiar 'formação alinhada' quando há indício real de aderência ao cargo alvo.
    Ex.: programador + biologia => False.
    """
    if not _has_nonempty_education(resume_data):
        return False
    edu_blob = _education_blob_lower(resume_data)
    if not edu_blob.strip():
        return False

    if not looks_like_tech_target(resume_data):
        target = (_data(resume_data).get("targetPosition") or "").strip().lower()
        if len(target) < 3:
            return False
        # Alvo não-tech: exige alguma sobreposição lexical simples com formação ou resumo
        summary = (_data(resume_data).get("summary") or "").lower()
        tokens = {t for t in re.findall(r"\w{3,}", target, flags=re.UNICODE)}
        edu_tokens = set(re.findall(r"\w{3,}", edu_blob + " " + summary, flags=re.UNICODE))
        return bool(tokens & edu_tokens)

    if _NON_TECH_EDU_RE.search(edu_blob) and not _TECH_EDU_RE.search(edu_blob):
        return False
    if _TECH_EDU_RE.search(edu_blob):
        return True

    skills = _data(resume_data).get("skills") or []
    tech_hits = 0
    for s in skills:
        name = s.get("name", s) if isinstance(s, dict) else s
        if name and _TECH_SKILL_RE.search(str(name)):
            tech_hits += 1
    return tech_hits >= 3


def education_tech_gap_suggestion(resume_data: dict[str, Any]) -> bool:
    """Sugestão: alvo tech mas formação não parece de TI."""
    if not _has_nonempty_education(resume_data):
        return False
    if not looks_like_tech_target(resume_data):
        return False
    return not education_aligned_with_target(resume_data)
