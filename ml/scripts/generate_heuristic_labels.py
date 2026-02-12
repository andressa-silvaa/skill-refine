"""
Generate heuristic labels for seniority (Task A) and quality flags (Task C).
Deterministic rules from policies.md; used as baseline and for semi-supervised data.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SENIORITY_LABELS = ("intern", "junior", "mid", "senior")
LANGUAGES = ("pt", "en", "es")

# Keywords per language (lowercased) that suggest seniority
SENIORITY_SIGNALS = {
    "pt": {
        "intern": ["estágio", "estagiário", "trainee"],
        "junior": ["júnior", "junior", "iniciante"],
        "mid": ["pleno", "mid", "analista"],
        "senior": ["sênior", "senior", "líder", "lider", "principal", "coordenador", "gerente", "lead"],
    },
    "en": {
        "intern": ["intern", "internship", "trainee"],
        "junior": ["junior", "entry", "associate"],
        "mid": ["mid", "mid-level", "analyst"],
        "senior": ["senior", "lead", "principal", "manager", "director", "head of"],
    },
    "es": {
        "intern": ["prácticas", "practicante", "pasante"],
        "junior": ["junior", "inicial"],
        "mid": ["semi-senior", "analista"],
        "senior": ["senior", "líder", "principal", "coordinador", "gerente", "jefe"],
    },
}

# Action verbs (presence -> has_action_verbs)
ACTION_VERBS = {
    "pt": ["liderou", "implementou", "desenvolveu", "gerenciou", "coordenou", "criou", "aumentou", "reduziu"],
    "en": ["led", "implemented", "developed", "managed", "coordinated", "created", "increased", "reduced"],
    "es": ["lideró", "implementó", "desarrolló", "gestionó", "coordinó", "creó", "aumentó", "redujo"],
}

LINK_PATTERN = re.compile(r"linkedin\.com|github\.com|portfolio|\.me/", re.I)
METRICS_PATTERN = re.compile(r"\d+%|\d+\s*(?:anos?|years?|años?)|R\$\s*\d+|\$\d+|%\s*(?:de|of)")


def heuristic_seniority(text: str, language: str) -> str:
    """
    Return seniority label from heuristic rules (policies.md).
    Default: mid. Prefer higher level when ambiguous.
    """
    text_lower = text.lower()
    signals = SENIORITY_SIGNALS.get(language, SENIORITY_SIGNALS["pt"])

    if any(s in text_lower for s in signals["senior"]):
        return "senior"
    if any(s in text_lower for s in signals["mid"]):
        return "mid"
    if any(s in text_lower for s in signals["junior"]):
        return "junior"
    if any(s in text_lower for s in signals["intern"]):
        return "intern"
    return "mid"


def heuristic_quality_flags(text: str, language: str) -> dict[str, bool]:
    """Return feature_flags for quality (has_metrics, has_links, has_action_verbs)."""
    text_lower = text.lower()
    verbs = ACTION_VERBS.get(language, ACTION_VERBS["pt"])
    return {
        "has_metrics": bool(METRICS_PATTERN.search(text)),
        "has_links": bool(LINK_PATTERN.search(text)),
        "has_action_verbs": any(v in text_lower for v in verbs),
    }


def heuristic_quality_score(feature_flags: dict[str, bool]) -> int:
    """Simple baseline score 0-100 from flags (explainable)."""
    score = 30
    if feature_flags.get("has_metrics"):
        score += 25
    if feature_flags.get("has_links"):
        score += 20
    if feature_flags.get("has_action_verbs"):
        score += 25
    return min(100, score)


def main() -> None:
    """CLI: read JSONL from stdin (input_text, language), write JSONL with label + feature_flags."""
    import sys

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        text = row.get("input_text", "")
        lang = row.get("language", "pt")
        if row.get("task_type") == "seniority":
            row["label"] = heuristic_seniority(text, lang)
            row["source"] = row.get("source", "heuristic")
        elif row.get("task_type") == "quality":
            flags = heuristic_quality_flags(text, lang)
            row["feature_flags"] = flags
            row["label_score"] = row.get("label_score", heuristic_quality_score(flags))
            row["source"] = row.get("source", "heuristic")
        print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
