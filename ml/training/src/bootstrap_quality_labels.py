"""
Populate quality_score and quality_level labels in train/val/test JSONL splits.

This bootstraps a first ordinal dataset for the quality task using a
deterministic rubric grounded in the labeling policies:
- metrics / KPIs
- action verbs
- relevant links
- leadership / architecture signals
- text structure and technical breadth

Usage:
  python ml/training/src/bootstrap_quality_labels.py
  python ml/training/src/bootstrap_quality_labels.py --splits_dir ml/data/splits
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


LINK_PATTERN = re.compile(r"linkedin\.com|github\.com|portfolio|portfólio|website|site pessoal|\.me/", re.I)
METRICS_PATTERN = re.compile(r"\d+%|\d+\s*(?:anos?|years?|años?|meses?|months?)|R\$\s*\d+|\$\d+|kpi|sla|okrs?", re.I)
ACTION_VERBS = {
    "pt": [
        "liderou", "implementou", "desenvolveu", "gerenciou", "coordenou", "criou",
        "aumentou", "reduziu", "otimizou", "automatizou", "definiu", "conduziu",
    ],
    "en": [
        "led", "implemented", "developed", "managed", "coordinated", "created",
        "increased", "reduced", "optimized", "automated", "defined", "drove",
    ],
    "es": [
        "lideró", "implementó", "desarrolló", "gestionó", "coordinó", "creó",
        "aumentó", "redujo", "optimizó", "automatizó", "definió", "impulsó",
    ],
}
LEADERSHIP_WORDS = re.compile(
    r"lider|lead|mentoria|mentoring|mentorship|coordena|coordinat|gest[aã]o|manager|roadmap|stakeholder|stakeholders",
    re.I,
)
ARCHITECTURE_WORDS = re.compile(
    r"arquitet|architecture|microsservi|microservice|integra[cç][aã]o|integration|platform|plataforma|governan|observability|observabilidade",
    re.I,
)
TECH_KEYWORDS = re.compile(
    r"\b(python|django|fastapi|react|sql|api|apis|etl|cloud|aws|azure|gcp|cypress|docker|kubernetes|nlp)\b",
    re.I,
)
SENIORITY_BASE = {
    "intern": 28,
    "junior": 42,
    "mid": 58,
    "senior": 72,
}


def parse_args() -> argparse.Namespace:
    default_splits = Path(__file__).resolve().parents[2] / "data" / "splits"
    parser = argparse.ArgumentParser(description="Populate quality_score and quality_level labels in dataset splits.")
    parser.add_argument("--splits_dir", type=Path, default=default_splits)
    parser.add_argument("--overwrite", action="store_true", help="Recompute quality_score and quality_level even when already present.")
    return parser.parse_args()


def _lang_code(language: str) -> str:
    if language.startswith("en"):
        return "en"
    if language.startswith("es"):
        return "es"
    return "pt"


def _stable_offset(resume_id: str) -> int:
    digest = hashlib.md5((resume_id or "").encode("utf-8")).hexdigest()
    return (int(digest[:4], 16) % 9) - 4


def _compute_quality_score(record: dict) -> int:
    text = str(record.get("resume_text") or (record.get("inputs") or {}).get("resume_text") or "")
    labels = record.setdefault("labels", {})
    seniority = str(labels.get("seniority") or "mid")
    language = str(record.get("language") or "pt-BR")
    lang = _lang_code(language)
    text_lower = text.lower()

    score = SENIORITY_BASE.get(seniority, 50)

    has_metrics = bool(METRICS_PATTERN.search(text_lower))
    has_links = bool(LINK_PATTERN.search(text_lower))
    action_count = sum(1 for verb in ACTION_VERBS[lang] if verb in text_lower)
    has_leadership = bool(LEADERSHIP_WORDS.search(text_lower))
    has_architecture = bool(ARCHITECTURE_WORDS.search(text_lower))
    tech_hits = len(set(match.group(0).lower() for match in TECH_KEYWORDS.finditer(text_lower)))
    sentence_count = len([part for part in re.split(r"[.!?]+", text) if part.strip()])
    word_count = len(text.split())

    if has_metrics:
        score += 14
    if has_links:
        score += 10
    if action_count >= 1:
        score += 8
    if action_count >= 3:
        score += 4
    if has_leadership:
        score += 8
    if has_architecture:
        score += 6
    if tech_hits >= 3:
        score += 5
    elif tech_hits >= 2:
        score += 3
    if 2 <= sentence_count <= 4:
        score += 3
    if 16 <= word_count <= 40:
        score += 2

    score += _stable_offset(str(record.get("resume_id") or record.get("id") or ""))
    return max(20, min(96, int(round(score))))


def _score_to_quality_level(score: int | float) -> str:
    score = float(score)
    if score < 40:
        return "poor"
    if score < 60:
        return "ok"
    return "strong"


def _rewrite_file(path: Path, overwrite: bool = False) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        record = json.loads(line)
        record.setdefault("labels", {})
        if overwrite or record["labels"].get("quality_score") is None:
            record["labels"]["quality_score"] = _compute_quality_score(record)
        if overwrite or not record["labels"].get("quality_level"):
            record["labels"]["quality_level"] = _score_to_quality_level(record["labels"]["quality_score"])
        output.append(json.dumps(record, ensure_ascii=False))
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    splits_dir = args.splits_dir.resolve()
    for name in ("train.jsonl", "val.jsonl", "test.jsonl"):
        target = splits_dir / name
        if target.exists():
            _rewrite_file(target, overwrite=args.overwrite)
            print(f"Updated {target}")


if __name__ == "__main__":
    main()
