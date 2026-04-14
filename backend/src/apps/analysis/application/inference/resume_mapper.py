"""
Convert Resume data (from DB/detail payload) to text sections for model input.
Supports headings per language (pt/en/es). Removes HTML, normalizes whitespace.
"""
from __future__ import annotations

import re
from typing import Any

from .types import ResumeSections

SECTION_TITLES: dict[str, dict[str, str]] = {
    "pt-BR": {
        "career_headline": "Objetivo e identificação",
        "summary": "Resumo",
        "experience": "Experiência Profissional",
        "education": "Formação",
        "skills": "Habilidades",
        "languages": "Idiomas",
        "contact": "Contato",
        "projects": "Projetos",
    },
    "pt": {
        "career_headline": "Objetivo e identificação",
        "summary": "Resumo",
        "experience": "Experiência Profissional",
        "education": "Formação",
        "skills": "Habilidades",
        "languages": "Idiomas",
        "contact": "Contato",
        "projects": "Projetos",
    },
    "en-US": {
        "career_headline": "Headline and target role",
        "summary": "Summary",
        "experience": "Work Experience",
        "education": "Education",
        "skills": "Skills",
        "languages": "Languages",
        "contact": "Contact",
        "projects": "Projects",
    },
    "en": {
        "career_headline": "Headline and target role",
        "summary": "Summary",
        "experience": "Work Experience",
        "education": "Education",
        "skills": "Skills",
        "languages": "Languages",
        "contact": "Contact",
        "projects": "Projects",
    },
    "es-ES": {
        "career_headline": "Objetivo y titular",
        "summary": "Resumen",
        "experience": "Experiencia Profesional",
        "education": "Formación",
        "skills": "Habilidades",
        "languages": "Idiomas",
        "contact": "Contacto",
        "projects": "Proyectos",
    },
    "es": {
        "career_headline": "Objetivo y titular",
        "summary": "Resumen",
        "experience": "Experiencia Profesional",
        "education": "Formación",
        "skills": "Habilidades",
        "languages": "Idiomas",
        "contact": "Contacto",
        "projects": "Proyectos",
    },
}

HTML_TAG = re.compile(r"<[^>]+>")
WHITESPACE = re.compile(r"\s+")
LANG_FALLBACK = "pt-BR"


def _normalize(text: str) -> str:
    """Remove HTML, collapse whitespace."""
    if not text:
        return ""
    t = HTML_TAG.sub(" ", str(text))
    t = WHITESPACE.sub(" ", t).strip()
    return t


def _titles(lang: str) -> dict[str, str]:
    lang = (lang or LANG_FALLBACK).strip()
    return SECTION_TITLES.get(lang, SECTION_TITLES.get(lang.split("-")[0], SECTION_TITLES[LANG_FALLBACK]))


def resume_to_text(resume_data: dict[str, Any], language: str = "pt-BR") -> ResumeSections:
    """
    Convert resume payload to sections dict and full_text.
    resume_data: dict with summary, contact, experiences, educations, skills, languages.
    (Matches resume_detail_payload["data"] structure.)
    """
    titles = _titles(language)
    data = resume_data.get("data", resume_data)

    cv_name = _normalize(str(resume_data.get("name") or ""))
    target_position = _normalize(str(data.get("targetPosition") or ""))
    career_lines = [ln for ln in (cv_name, target_position) if ln]
    career_block = "\n".join(career_lines)

    summary = _normalize(data.get("summary") or "")
    contact_data = data.get("contact") or {}
    experiences = data.get("experiences") or []
    educations = data.get("educations") or []
    skills = data.get("skills") or []
    languages_list = data.get("languages") or []

    # Experience
    exp_parts = []
    for exp in experiences:
        company = _normalize(exp.get("company") or "")
        position = _normalize(exp.get("position") or "")
        start = exp.get("startDate") or ""
        end = exp.get("endDate") or ""
        header = f"{position} at {company}" if company else position
        if start or end:
            header += f" ({start} - {end})"
        if header:
            exp_parts.append(header)
        bullets = exp.get("description") or []
        for b in bullets:
            bullet_text = _normalize(str(b))
            if bullet_text:
                exp_parts.append(f"- {bullet_text}")
    experience = "\n".join(exp_parts)

    # Education
    edu_parts = []
    for edu in educations:
        institution = _normalize(edu.get("institution") or "")
        course = _normalize(edu.get("course") or "")
        degree = _normalize(edu.get("degree") or "")
        parts = [p for p in [degree, course, institution] if p]
        if parts:
            edu_parts.append(", ".join(parts))
    education = "\n".join(edu_parts)

    # Skills: comma-separated
    skill_names = []
    for s in skills:
        name = _normalize(s.get("name") if isinstance(s, dict) else str(s))
        if name:
            skill_names.append(name)
    skills_text = ", ".join(skill_names)

    # Languages
    lang_parts = []
    for l in languages_list:
        name = _normalize(l.get("name") if isinstance(l, dict) else str(l))
        level = l.get("level", "") if isinstance(l, dict) else ""
        if name:
            lang_parts.append(f"{name} ({level})" if level else name)
    languages_text = ", ".join(lang_parts)

    # Contact (links only for analysis; mask PII in full text)
    contact_parts = []
    for k in ("linkedin", "github", "portfolio", "website"):
        v = contact_data.get(k) or ""
        if _normalize(v):
            contact_parts.append(f"[{k.upper()}]")
    contact = " ".join(contact_parts) if contact_parts else ""

    # Full text with headings (nome do CV + cargo alvo entram no texto do modelo/heurística)
    sections_list = []
    if career_block:
        sections_list.append(f"{titles['career_headline']}\n{career_block}")
    if summary:
        sections_list.append(f"{titles['summary']}\n{summary}")
    if experience:
        sections_list.append(f"{titles['experience']}\n{experience}")
    if education:
        sections_list.append(f"{titles['education']}\n{education}")
    if skills_text:
        sections_list.append(f"{titles['skills']}\n{skills_text}")
    if languages_text:
        sections_list.append(f"{titles['languages']}\n{languages_text}")
    if contact:
        sections_list.append(f"{titles['contact']}\n{contact}")

    full_text = "\n\n".join(sections_list)

    return ResumeSections(
        summary=summary,
        experience=experience,
        education=education,
        skills=skills_text,
        languages=languages_text,
        contact=contact,
        projects="",
        full_text=full_text,
    )
