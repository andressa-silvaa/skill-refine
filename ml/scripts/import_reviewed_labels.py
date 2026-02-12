"""
Reimport reviewed labels (CSV/JSONL from export_for_review) and merge into dataset as gold (label_source=revisado).
Produces output JSONL with reviewed_seniority / reviewed_quality_score merged into labels; label_source set to 'revisado'.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

def run(review_path: Path, original_path: Path, output_path: Path, *, format: str = "auto") -> int:
    """
    review_path: CSV or JSONL with id/resume_id, reviewed_seniority, reviewed_quality_score, reviewed_notes.
    original_path: Original JSONL (unified records with id or resume_id).
    output_path: JSONL with labels updated from review; label_source=revisado where reviewed.
    format: 'csv', 'jsonl', or 'auto' (detect by extension). Returns count of updated records.
    """
    if format == "auto":
        format = "csv" if review_path.suffix.lower() == ".csv" else "jsonl"
    reviewed: dict[str, dict] = {}
    if format == "csv":
        with open(review_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rid = row.get("resume_id") or row.get("id") or ""
                if not rid:
                    continue
                reviewed[rid] = {
                    "reviewed_seniority": (row.get("reviewed_seniority") or "").strip(),
                    "reviewed_quality_score": row.get("reviewed_quality_score"),
                    "reviewed_notes": (row.get("reviewed_notes") or "").strip(),
                }
    else:
        with open(review_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                rid = row.get("resume_id") or row.get("id") or ""
                if not rid:
                    continue
                reviewed[rid] = {
                    "reviewed_seniority": (row.get("reviewed_seniority") or "").strip(),
                    "reviewed_quality_score": row.get("reviewed_quality_score"),
                    "reviewed_notes": (row.get("reviewed_notes") or "").strip(),
                }
    count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(original_path, encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            rid = rec.get("resume_id") or rec.get("id") or ""
            rev = reviewed.get(rid) if rid else None
            labels = dict(rec.get("labels") or {})
            if rev:
                if rev["reviewed_seniority"]:
                    labels["seniority"] = rev["reviewed_seniority"]
                if rev["reviewed_quality_score"] != "" and rev["reviewed_quality_score"] is not None:
                    try:
                        labels["quality_score"] = int(float(rev["reviewed_quality_score"]))
                    except (ValueError, TypeError):
                        pass
                rec["labels"] = labels
                rec["label_source"] = "revisado"
                if rev["reviewed_notes"]:
                    rec["review_notes"] = rev["reviewed_notes"]
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Import reviewed labels into dataset (gold v1)")
    p.add_argument("review", type=Path, help="Reviewed CSV or JSONL (from export_for_review)")
    p.add_argument("original", type=Path, help="Original JSONL")
    p.add_argument("-o", "--output", type=Path, required=True, help="Output JSONL (gold)")
    p.add_argument("--format", type=str, default="auto", choices=["auto", "csv", "jsonl"])
    args = p.parse_args()
    n = run(args.review, args.original, args.output, format=args.format)
    print(f"Updated {n} records with reviewed labels -> {args.output}", flush=True)


if __name__ == "__main__":
    main()
