"""
Export dataset to CSV/JSONL for manual label review. Includes fields to edit: label, label_score, label_source.
Reimport with import_reviewed_labels.py to produce gold (v1) dataset.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from uuid import uuid4

REVIEW_FIELDS = ["resume_id", "language", "label_seniority", "label_quality_score", "label_source", "reviewed_seniority", "reviewed_quality_score", "reviewed_notes"]


def run(
    input_path: Path,
    output_path: Path,
    *,
    format: str = "csv",
    max_rows: int | None = None,
    sample_ratio: float | None = None,
    seed: int = 42,
    include_text_preview: bool = True,
    preview_len: int = 200,
) -> int:
    """
    Read JSONL (unified or task rows), export for review with columns for revised labels.
    format: 'csv' or 'jsonl'. sample_ratio: randomly sample this fraction (e.g. 0.2 for 20%).
    Returns count.
    """
    import random
    rows: list[dict] = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            text = rec.get("resume_text") or rec.get("input_text") or ""
            labels = rec.get("labels") or {}
            out = {
                "id": rec.get("id") or str(uuid4()),
                "resume_id": rec.get("resume_id") or "",
                "language": rec.get("language", ""),
                "label_seniority": labels.get("seniority", ""),
                "label_quality_score": labels.get("quality_score", ""),
                "label_source": rec.get("label_source", "heuristic"),
                "reviewed_seniority": "",
                "reviewed_quality_score": "",
                "reviewed_notes": "",
            }
            if include_text_preview:
                out["text_preview"] = text[:preview_len] + ("..." if len(text) > preview_len else "")
            rows.append(out)

    if sample_ratio is not None and 0 < sample_ratio < 1:
        rng = random.Random(seed)
        n_sample = max(1, int(len(rows) * sample_ratio))
        rows = rng.sample(rows, min(n_sample, len(rows)))
    elif max_rows is not None and max_rows > 0:
        rows = rows[:max_rows]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = len(rows)
    if format == "csv":
        if not rows:
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else REVIEW_FIELDS + ["text_preview"])
                writer.writeheader()
        else:
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return count


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Export dataset for manual label review (CSV/JSONL)")
    p.add_argument("input", type=Path, help="Input JSONL")
    p.add_argument("-o", "--output", type=Path, required=True, help="Output CSV or JSONL")
    p.add_argument("--format", type=str, default="csv", choices=["csv", "jsonl"])
    p.add_argument("--max-rows", type=int, help="Max rows to export")
    p.add_argument("--sample-ratio", type=float, help="Randomly sample this fraction (e.g. 0.2 for 20%%)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-preview", action="store_true", help="Do not include text_preview")
    p.add_argument("--preview-len", type=int, default=200)
    args = p.parse_args()
    suf = args.output.suffix.lower()
    fmt = "csv" if suf == ".csv" else "jsonl"
    if args.format != "csv" and args.format != "jsonl":
        fmt = args.format
    n = run(
        args.input,
        args.output,
        format=fmt,
        max_rows=args.max_rows,
        sample_ratio=args.sample_ratio,
        seed=args.seed,
        include_text_preview=not args.no_preview,
        preview_len=args.preview_len,
    )
    print(f"Exported {n} rows for review -> {args.output}", flush=True)


if __name__ == "__main__":
    main()
