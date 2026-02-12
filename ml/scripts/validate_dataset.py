"""
Validate dataset against schema and label sets: required fields, allowed enums, language distribution.
Exit 0 if valid, non-zero and report errors otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Load label sets from labeling/
SCRIPT_DIR = Path(__file__).resolve().parent
LABELING_DIR = SCRIPT_DIR.parent / "labeling"
SECTION_LABELS: list[str] = []
SENIORITY_LABELS: tuple[str, ...] = ("intern", "junior", "mid", "senior")
LANGUAGES = ("pt", "en", "es")


def _load_section_labels() -> list[str]:
    p = LABELING_DIR / "section_labels.json"
    if not p.exists():
        return ["EXPERIENCE", "EDUCATION", "SKILLS", "PROJECTS", "SUMMARY", "CONTACT", "OTHER"]
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("labels", [])


def validate_unified_row(row: dict, index: int) -> list[str]:
    """Validate unified dataset_item schema: id, language, resume_id, resume_text, labels, heuristics, source, created_at."""
    errs: list[str] = []
    if not row.get("resume_id"):
        errs.append(f"row {index}: missing resume_id")
    text = row.get("resume_text") or row.get("input_text")
    if not text:
        errs.append(f"row {index}: missing resume_text or input_text")
    lang = row.get("language")
    if lang:
        lang_norm = (str(lang).replace("-BR", "").replace("-US", "").replace("-ES", ""))
        if lang_norm not in LANGUAGES:
            errs.append(f"row {index}: invalid language {lang}")
    else:
        errs.append(f"row {index}: missing language")
    src = row.get("source")
    if src and src not in ("public", "synthetic", "anonymized"):
        errs.append(f"row {index}: invalid source {src}")
    labels = row.get("labels")
    if labels and isinstance(labels, dict):
        sr = labels.get("seniority")
        if sr and sr not in SENIORITY_LABELS:
            errs.append(f"row {index}: invalid labels.seniority {sr}")
    return errs


def validate_row(row: dict, index: int) -> list[str]:
    """Return list of error strings for this row (task-type or unified)."""
    errs: list[str] = []

    task_type = row.get("task_type")
    if not task_type:
        if row.get("resume_id") and (row.get("resume_text") or row.get("input_text")):
            return validate_unified_row(row, index)
        errs.append(f"row {index}: missing task_type and not unified (resume_id + resume_text)")
        return errs
    if task_type not in ("seniority", "sections", "quality", "matching"):
        errs.append(f"row {index}: invalid task_type {task_type}")

    lang = row.get("language")
    if not lang:
        errs.append(f"row {index}: missing language")
    elif lang not in LANGUAGES:
        errs.append(f"row {index}: invalid language {lang}")

    if task_type == "seniority":
        label = row.get("label")
        if not label:
            errs.append(f"row {index}: missing label")
        elif label not in SENIORITY_LABELS:
            errs.append(f"row {index}: invalid seniority label {label}")
        if not row.get("input_text"):
            errs.append(f"row {index}: missing input_text")

    elif task_type == "sections":
        global SECTION_LABELS
        if not SECTION_LABELS:
            SECTION_LABELS = _load_section_labels()
        label = row.get("label")
        if not label:
            errs.append(f"row {index}: missing label")
        elif label not in SECTION_LABELS:
            errs.append(f"row {index}: invalid section label {label}")
        if not row.get("line_text") and not row.get("input_text"):
            errs.append(f"row {index}: missing line_text or input_text")
        if not row.get("resume_id"):
            errs.append(f"row {index}: missing resume_id for sections")

    elif task_type == "quality":
        score = row.get("label_score")
        if score is None:
            errs.append(f"row {index}: missing label_score")
        elif not isinstance(score, (int, float)) or score < 0 or score > 100:
            errs.append(f"row {index}: label_score must be 0-100")
        if not row.get("input_text"):
            errs.append(f"row {index}: missing input_text")

    elif task_type == "matching":
        if not row.get("job_text"):
            errs.append(f"row {index}: missing job_text")
        if not row.get("resume_text"):
            errs.append(f"row {index}: missing resume_text")
        if not row.get("resume_id"):
            errs.append(f"row {index}: missing resume_id for matching")

    return errs


def run(input_path: Path) -> tuple[list[str], dict]:
    """Validate JSONL file. Return (list of errors, stats dict)."""
    errors: list[str] = []
    stats: dict = {"total": 0, "by_task": {}, "by_language": {}}
    if not input_path.exists():
        return [f"File not found: {input_path}"], stats

    with open(input_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"line {i+1}: invalid JSON - {e}")
                continue
            stats["total"] += 1
            task = row.get("task_type") or "unified"
            stats["by_task"][task] = stats["by_task"].get(task, 0) + 1
            lang = row.get("language", "?")
            if isinstance(lang, str):
                lang_norm = lang.replace("-BR", "").replace("-US", "").replace("-ES", "")
            else:
                lang_norm = str(lang)
            stats["by_language"][lang_norm] = stats["by_language"].get(lang_norm, 0) + 1
            errors.extend(validate_row(row, i + 1))

    return errors, stats


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Validate dataset JSONL")
    p.add_argument("input", type=Path, help="Input JSONL")
    p.add_argument("--stats", action="store_true", help="Print stats even if invalid")
    args = p.parse_args()
    errors, stats = run(args.input)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        if args.stats:
            print(json.dumps(stats, indent=2))
        sys.exit(1)
    print("OK")
    print(json.dumps(stats, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
