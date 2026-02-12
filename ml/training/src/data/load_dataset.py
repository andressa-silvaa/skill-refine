"""
Load JSONL dataset; validate fields per task; normalize to canonical shape (inputs.resume_text, labels.*).
Supports both: top-level resume_text/labels and nested inputs/labels.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SENIORITY_LABELS = ("intern", "junior", "mid", "senior")
LANGUAGE_NORMALIZE = {"pt": "pt-BR", "pt-BR": "pt-BR", "en": "en-US", "en-US": "en-US", "es": "es-ES", "es-ES": "es-ES"}


def _normalize_lang(lang: str) -> str:
    return LANGUAGE_NORMALIZE.get((lang or "pt").strip(), "pt-BR")


def _normalize_record(raw: dict) -> dict:
    """Canonical: inputs.resume_text, inputs.job_text, labels.seniority, labels.quality_score, labels.sections, labels.matching_score."""
    inputs = raw.get("inputs") or {}
    labels = raw.get("labels") or {}
    resume_text = inputs.get("resume_text") or raw.get("resume_text") or raw.get("input_text") or ""
    job_text = inputs.get("job_text") or raw.get("job_text") or ""
    lang = _normalize_lang(raw.get("language", "pt"))
    return {
        "id": raw.get("id", ""),
        "language": lang,
        "resume_id": raw.get("resume_id", ""),
        "inputs": {"resume_text": resume_text, "job_text": job_text},
        "labels": {
            "seniority": labels.get("seniority"),
            "quality_score": labels.get("quality_score"),
            "sections": labels.get("sections"),
            "matching_score": labels.get("matching_score"),
        },
        "sections": raw.get("sections"),  # for ablations
    }


def _validate_seniority(record: dict) -> list[str]:
    errs = []
    text = (record.get("inputs") or {}).get("resume_text") or ""
    if not text.strip():
        errs.append("inputs.resume_text (or resume_text) required")
    lab = (record.get("labels") or {}).get("seniority")
    if not lab:
        errs.append("labels.seniority required")
    elif lab not in SENIORITY_LABELS:
        errs.append(f"labels.seniority must be one of {SENIORITY_LABELS}")
    return errs


def _validate_quality(record: dict) -> list[str]:
    errs = []
    text = (record.get("inputs") or {}).get("resume_text") or ""
    if not text.strip():
        errs.append("inputs.resume_text (or resume_text) required")
    lab = (record.get("labels") or {}).get("quality_score")
    if lab is None:
        errs.append("labels.quality_score required")
    elif not isinstance(lab, (int, float)) or lab < 0 or lab > 100:
        errs.append("labels.quality_score must be 0-100")
    return errs


def _validate_sections(record: dict) -> list[str]:
    errs = []
    lab = (record.get("labels") or {}).get("sections")
    if lab is None:
        errs.append("labels.sections required (list of {tokens, tags} or sentence+label)")
    return errs


def _validate_matching(record: dict) -> list[str]:
    errs = []
    inputs = record.get("inputs") or {}
    if not (inputs.get("job_text") or "").strip():
        errs.append("inputs.job_text required for matching")
    if not (inputs.get("resume_text") or "").strip():
        errs.append("inputs.resume_text required for matching")
    lab = (record.get("labels") or {}).get("matching_score")
    if lab is None:
        errs.append("labels.matching_score required")
    return errs


VALIDATORS = {
    "seniority": _validate_seniority,
    "sections": _validate_sections,
    "quality": _validate_quality,
    "matching": _validate_matching,
}


def load_jsonl(path: Path, task: str, languages: list[str] | None = None, ablations: list[str] | None = None, drop_section_value: str | None = None) -> list[dict]:
    """
    Load JSONL; normalize; filter by languages; validate per task; apply ablations to resume_text.
    Returns list of canonical records. Fails with clear message if required fields missing.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    validator = VALIDATORS.get(task)
    if not validator:
        raise ValueError(f"Unknown task: {task}. Use one of {list(VALIDATORS)}")
    lang_set = set(languages) if languages else None
    records = []
    for i, line in enumerate(path.read_text(encoding="utf-8").strip().splitlines()):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON line {i+1} in {path}: {e}")
        rec = _normalize_record(raw)
        if lang_set and rec["language"] not in lang_set:
            continue
        errs = validator(rec)
        if errs:
            raise ValueError(f"Line {i+1} ({path}): {'; '.join(errs)}")
        # Ablations on resume_text
        if ablations:
            from .preprocess import apply_ablations
            text = rec["inputs"]["resume_text"]
            text = apply_ablations(text, rec["language"], ablations, drop_section_value=drop_section_value, sections=rec.get("sections"))
            rec["inputs"]["resume_text"] = text
        records.append(rec)
    return records


def load_splits(
    splits_dir: Path,
    task: str,
    train_file: str = "train.jsonl",
    val_file: str = "val.jsonl",
    test_file: str = "test.jsonl",
    languages: list[str] | None = None,
    ablations: list[str] | None = None,
    drop_section_value: str | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Load train, val, test JSONL. Returns (train, val, test)."""
    train = load_jsonl(splits_dir / train_file, task, languages=languages, ablations=ablations, drop_section_value=drop_section_value) if (splits_dir / train_file).exists() else []
    val = load_jsonl(splits_dir / val_file, task, languages=languages) if (splits_dir / val_file).exists() else []
    test = load_jsonl(splits_dir / test_file, task, languages=languages) if (splits_dir / test_file).exists() else []
    return train, val, test
