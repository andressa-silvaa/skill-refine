"""
Bootstrap labels using heuristics loaded from labeling/heuristics/*.json.
Produces/updates labels and heuristics on unified records or task-specific rows.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LABELING_DIR = SCRIPT_DIR.parent / "labeling"
HEURISTICS_DIR = LABELING_DIR / "heuristics"

LANGUAGES = ("pt", "en", "es")
SENIORITY_LABELS = ("intern", "junior", "mid", "senior")

# Fallback if JSON missing (same as generate_heuristic_labels)
SENIORITY_SIGNALS = {
    "pt": {"intern": ["estágio", "estagiário", "trainee"], "junior": ["júnior", "junior", "iniciante"], "mid": ["pleno", "mid", "analista"], "senior": ["sênior", "senior", "líder", "lider", "principal", "coordenador", "gerente", "lead"]},
    "en": {"intern": ["intern", "internship", "trainee"], "junior": ["junior", "entry", "associate"], "mid": ["mid", "mid-level", "analyst"], "senior": ["senior", "lead", "principal", "manager", "director", "head of"]},
    "es": {"intern": ["prácticas", "practicante", "pasante"], "junior": ["junior", "inicial"], "mid": ["semi-senior", "analista"], "senior": ["senior", "líder", "principal", "coordinador", "gerente", "jefe"]},
}

LINK_PATTERN = re.compile(r"linkedin\.com|github\.com|portfolio|\.me/", re.I)
METRICS_PATTERN = re.compile(r"\d+%|\d+\s*(?:anos?|years?|años?)|R\$\s*\d+|\$\d+|%\s*(?:de|of)")


def load_verbs(language: str) -> list[str]:
    path = HEURISTICS_DIR / f"verbs_{language}.json"
    if not path.exists():
        path = HEURISTICS_DIR / "verbs_pt.json"
    if not path.exists():
        return ["liderou", "implementou", "desenvolveu", "gerenciou", "coordenou", "criou", "aumentou", "reduziu"] if language == "pt" else ["led", "implemented", "developed", "managed", "coordinated", "created", "increased", "reduced"]
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("verbs", [])


def heuristic_seniority(text: str, language: str) -> str:
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
    verbs = load_verbs(language)
    text_lower = text.lower()
    return {
        "has_metrics": bool(METRICS_PATTERN.search(text)),
        "has_links": bool(LINK_PATTERN.search(text)),
        "has_action_verbs": any(v in text_lower for v in verbs),
    }


def heuristic_quality_score(flags: dict[str, bool]) -> int:
    score = 30
    if flags.get("has_metrics"):
        score += 25
    if flags.get("has_links"):
        score += 20
    if flags.get("has_action_verbs"):
        score += 25
    return min(100, score)


def label_record(record: dict) -> dict:
    """
    Add/overwrite labels and heuristics on a unified record (resume_text, language).
    Sets labels.seniority, labels.quality_score, heuristics (has_metrics, has_links, has_action_verbs), label_source.
    """
    out = dict(record)
    text = out.get("resume_text") or out.get("input_text") or ""
    lang = (out.get("language") or "pt").replace("-BR", "").replace("-US", "").replace("-ES", "")
    if lang not in LANGUAGES:
        lang = "pt"
    labels = out.get("labels") or {}
    heuristics = heuristic_quality_flags(text, lang)
    # Preserve seniority from synthetic generator (ground truth); otherwise use heuristic
    if out.get("label_source") != "synthetic" or not labels.get("seniority"):
        labels["seniority"] = heuristic_seniority(text, lang)
    labels["quality_score"] = heuristic_quality_score(heuristics)
    out["heuristics"] = heuristics
    out["labels"] = labels
    out["label_source"] = out.get("label_source") or "heuristic"
    return out


def run(input_path: Path, output_path: Path) -> int:
    """Read JSONL, label each record, write JSONL. Returns count."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(input_path, encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            out = label_record(rec)
            fout.write(json.dumps(out, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Bootstrap labels with heuristics (from labeling/heuristics/*.json)")
    p.add_argument("input", type=Path, help="Input JSONL (unified or task rows)")
    p.add_argument("-o", "--output", type=Path, required=True, help="Output JSONL")
    args = p.parse_args()
    n = run(args.input, args.output)
    print(f"Labeled {n} records -> {args.output}", flush=True)


if __name__ == "__main__":
    main()
