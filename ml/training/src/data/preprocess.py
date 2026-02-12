"""Preprocessing and ablations: remove_stopwords, drop_section, drop_metrics_numbers."""
from __future__ import annotations

import re
from typing import Any

# Minimal stopwords per language (for ablation)
STOPWORDS_PT = {"de", "da", "do", "dos", "das", "e", "em", "no", "na", "um", "uma", "o", "a", "os", "as", "para", "por", "com", "que", "se", "ao", "à", "dos", "das", "ao", "aos"}
STOPWORDS_EN = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "with", "by", "and", "or", "is", "are", "was", "were", "be", "been", "being"}
STOPWORDS_ES = {"de", "la", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un", "para", "con", "no", "una", "su", "al", "lo", "como", "más", "pero", "sus", "le", "ya", "o", "este", "sí", "porque", "esta", "entre", "cuando", "muy", "sin", "sobre", "también", "me", "hasta", "hay", "donde", "han", "quien", "desde", "todo", "nos", "durante", "estados", "todos", "uno", "les", "ni", "contra", "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mí", "antes", "algunos", "qué", "unos", "yo", "otro", "otras", "otra", "él", "tanto", "esa", "estos", "mucho", "quienes", "nada", "muchos", "cual", "sea", "poco", "ella", "están", "estas", "algunas", "algo", "nosotros"}


def _lang_code(language: str) -> str:
    lang = (language or "pt").upper()
    if "PT" in lang or lang == "PT-BR":
        return "pt"
    if "EN" in lang or lang == "EN-US":
        return "en"
    if "ES" in lang or lang == "ES-ES":
        return "es"
    return "pt"


def remove_stopwords(text: str, language: str) -> str:
    if _lang_code(language) == "en":
        stop = STOPWORDS_EN
    elif _lang_code(language) == "es":
        stop = STOPWORDS_ES
    else:
        stop = STOPWORDS_PT
    words = text.split()
    return " ".join(w for w in words if w.lower() not in stop)


def drop_metrics_numbers(text: str) -> str:
    """Remove numbers, %, R$, $, and similar metric symbols."""
    t = re.sub(r"\d+%", " ", text)
    t = re.sub(r"R\s*\$\s*\d+", " ", t)
    t = re.sub(r"\$\s*\d+", " ", t)
    t = re.sub(r"\d+(?:[.,]\d+)*", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def drop_section(text: str, section_name: str, sections: dict[str, str] | None = None) -> str:
    """
    Remove a section from text. If sections dict is provided (summary, experience, education, skills),
    rebuild text without that section; else do a simple heuristic (remove lines containing section header).
    """
    if sections and section_name in sections:
        out_sections = {k: v for k, v in sections.items() if k != section_name and v}
        return "\n\n".join(out_sections.values()).strip()
    # Heuristic: remove block after common headers
    section_lower = section_name.lower()
    headers_pt = {"experience": "experiência", "education": "formação", "skills": "habilidades"}
    headers_en = {"experience": "experience", "education": "education", "skills": "skills"}
    headers_es = {"experience": "experiencia", "education": "formación", "skills": "habilidades"}
    for d in (headers_pt, headers_en, headers_es):
        if section_lower in d and d[section_lower] in text.lower():
            # Simple: split by double newline and drop block that starts with this header
            parts = re.split(r"\n\s*\n", text)
            out = []
            skip = False
            for p in parts:
                if d[section_lower] in p.lower() and len(p) < 100:
                    skip = True
                    continue
                if skip and p.strip():
                    skip = False
                if not skip:
                    out.append(p)
            return "\n\n".join(out).strip()
    return text


def apply_ablations(
    text: str,
    language: str,
    ablations: list[str],
    *,
    drop_section_value: str | None = None,
    sections: dict[str, str] | None = None,
) -> str:
    """
    ablations: list of 'remove_stopwords', 'drop_section', 'drop_metrics_numbers'.
    drop_section_value: e.g. 'experience' (used when 'drop_section' in ablations).
    """
    t = text
    for ab in ablations:
        if ab == "remove_stopwords":
            t = remove_stopwords(t, language)
        elif ab == "drop_metrics_numbers":
            t = drop_metrics_numbers(t)
        elif ab == "drop_section" and drop_section_value:
            t = drop_section(t, drop_section_value, sections)
    return " ".join(t.split())
