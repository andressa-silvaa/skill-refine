"""
Orchestrate pipeline: read raw or intermediate data, normalize, generate heuristics, validate, split.
Usage:
  python build_dataset.py --input data/raw/samples.jsonl --output-dir data/processed --splits-dir data/splits
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ML_ROOT = SCRIPT_DIR.parent


def run_script(name: str, stdin: bytes | None = None, args: list[str] | None = None) -> None:
    """Run a script in ml/scripts with optional stdin and extra args."""
    cmd = [sys.executable, str(SCRIPT_DIR / name)]
    if args:
        cmd.extend(args)
    subprocess.run(cmd, input=stdin, check=True)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Build dataset: normalize -> heuristics -> validate -> split")
    p.add_argument("--input", type=Path, required=True, help="Input JSONL (raw or with task_type)")
    p.add_argument("--output-dir", type=Path, default=ML_ROOT / "data" / "processed")
    p.add_argument("--splits-dir", type=Path, default=ML_ROOT / "data" / "splits")
    p.add_argument("--skip-heuristic", action="store_true", help="Do not run generate_heuristic_labels")
    p.add_argument("--skip-split", action="store_true", help="Do not run split_by_resume_id")
    args = p.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    processed_path = args.output_dir / "dataset.jsonl"

    # 1) Normalize: if input has input_text, normalize and set language
    rows: list[dict] = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    # Optional: run normalize_resume on each input_text (inline for simplicity)
    try:
        from normalize_resume import normalize_resume_text
    except ImportError:
        normalize_resume_text = None

    if normalize_resume_text:
        for row in rows:
            if row.get("input_text"):
                norm, lang = normalize_resume_text(row["input_text"], language=row.get("language"))
                row["input_text"] = norm
                row["language"] = lang
            if row.get("line_text"):
                norm, lang = normalize_resume_text(row["line_text"], language=row.get("language"))
                row["line_text"] = norm
                row["language"] = row.get("language") or lang

    # 2) Heuristic labels (if not skip)
    if not args.skip_heuristic:
        try:
            from generate_heuristic_labels import (
                heuristic_quality_flags,
                heuristic_quality_score,
                heuristic_seniority,
            )
            for row in rows:
                task = row.get("task_type")
                text = row.get("input_text") or row.get("line_text") or ""
                lang = row.get("language", "pt")
                if task == "seniority" and not row.get("label"):
                    row["label"] = heuristic_seniority(text, lang)
                    row["source"] = "heuristic"
                elif task == "quality" and "label_score" not in row:
                    flags = heuristic_quality_flags(text, lang)
                    row["feature_flags"] = flags
                    row["label_score"] = heuristic_quality_score(flags)
                    row["source"] = "heuristic"
        except ImportError:
            pass

    # Write processed
    with open(processed_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # 3) Validate (non-fatal: report only)
    r = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "validate_dataset.py"), str(processed_path), "--stats"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
    else:
        print(r.stdout)

    # 4) Split
    if not args.skip_split:
        run_script("split_by_resume_id.py", args=[str(processed_path), "-o", str(args.splits_dir)])

    print("Done:", processed_path)
    run_script("stats_report.py", args=[str(processed_path)])


if __name__ == "__main__":
    main()
