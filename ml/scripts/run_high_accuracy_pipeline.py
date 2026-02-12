"""
Full pipeline for high-accuracy seniority model:
1. Generate 800-1500 synthetic resumes (balanced by seniority)
2. Preprocess + label with heuristics (preserve synthetic labels)
3. Export 15-20% for manual review
4. Split by resume_id
5. Train TF-IDF + LogReg (lightweight, no GPU)
6. If accuracy < 0.9: try DistilBERT, then BERTimbau

Usage:
  cd ml/scripts
  python run_high_accuracy_pipeline.py
  # After manual review (optional): edit labeling/review_exports/for_review.csv
  # then: python import_reviewed_labels.py ... -o ... && re-run from step 4
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ML_ROOT = SCRIPT_DIR.parent
DATA_RAW = ML_ROOT / "data" / "raw"
DATA_PROCESSED = ML_ROOT / "data" / "processed"
DATA_SPLITS = ML_ROOT / "data" / "splits"
REVIEW_EXPORTS = ML_ROOT / "labeling" / "review_exports"
MODELS_DIR = ML_ROOT / "models"
REPORTS_DIR = ML_ROOT / "reports"

TARGET_ACCURACY = 0.9
SYNTHETIC_COUNT = 1000
SAMPLE_RATIO = 0.2  # 20% for manual review


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    """Run command, exit on failure."""
    cwd = cwd or SCRIPT_DIR
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    r = subprocess.run(cmd, cwd=str(cwd))
    if r.returncode != 0:
        sys.exit(r.returncode)


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Run high-accuracy seniority pipeline")
    p.add_argument("--count", type=int, default=SYNTHETIC_COUNT, help="Number of synthetic resumes")
    p.add_argument("--skip-generation", action="store_true", help="Skip generation, use existing raw data")
    p.add_argument("--skip-review-export", action="store_true", help="Skip export for manual review")
    p.add_argument("--with-reviewed", type=Path, help="Path to reviewed CSV (from export_for_review) to merge")
    p.add_argument("--target-acc", type=float, default=TARGET_ACCURACY)
    args = p.parse_args()

    print("=== 1. Generate synthetic resumes (balanced seniority) ===")
    raw_path = DATA_RAW / "synthetic_balanced.jsonl"
    if not args.skip_generation:
        run_cmd([
            sys.executable,
            str(SCRIPT_DIR / "generate_synthetic_resumes.py"),
            "-n", str(args.count),
            "--language", "pt",
            "--balance-seniority",
            "--no-balance-bad",  # Keep all "good" for cleaner signal
            "-o", str(raw_path),
        ])
        print(f"  Generated {args.count} resumes -> {raw_path}")
    else:
        if not raw_path.exists():
            print(f"  ERROR: {raw_path} not found. Run without --skip-generation.")
            sys.exit(1)
        print(f"  Using existing {raw_path}")

    print("\n=== 2. Preprocess ===")
    preprocessed_path = DATA_PROCESSED / "preprocessed.jsonl"
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    run_cmd([
        sys.executable,
        str(SCRIPT_DIR / "preprocess.py"),
        str(raw_path),
        "-o", str(preprocessed_path),
    ])

    print("\n=== 3. Label with heuristics (preserve synthetic seniority) ===")
    labeled_path = DATA_PROCESSED / "labeled.jsonl"
    run_cmd([
        sys.executable,
        str(SCRIPT_DIR / "label_with_heuristics.py"),
        str(preprocessed_path),
        "-o", str(labeled_path),
    ])

    # Merge reviewed labels if provided
    if args.with_reviewed and args.with_reviewed.exists():
        print("\n=== 3b. Merge reviewed labels ===")
        gold_path = DATA_PROCESSED / "gold.jsonl"
        run_cmd([
            sys.executable,
            str(SCRIPT_DIR / "import_reviewed_labels.py"),
            str(args.with_reviewed),
            str(labeled_path),
            "-o", str(gold_path),
        ])
        labeled_path = gold_path
        print(f"  Merged review -> {gold_path}")

    if not args.skip_review_export:
        print("\n=== 4. Export 15-20% for manual review ===")
        REVIEW_EXPORTS.mkdir(parents=True, exist_ok=True)
        review_csv = REVIEW_EXPORTS / "for_review.csv"
        run_cmd([
            sys.executable,
            str(SCRIPT_DIR / "export_for_review.py"),
            str(labeled_path),
            "-o", str(review_csv),
            "--sample-ratio", str(SAMPLE_RATIO),
        ])
        print(f"  Exported to {review_csv}")
        print("  -> Edit reviewed_seniority and reviewed_quality_score columns.")
        print("  -> Re-run with: --with-reviewed ml/labeling/review_exports/for_review.csv")

    print("\n=== 5. Split by resume_id ===")
    DATA_SPLITS.mkdir(parents=True, exist_ok=True)
    run_cmd([
        sys.executable,
        str(SCRIPT_DIR / "split_by_resume_id.py"),
        str(labeled_path),
        "-o", str(DATA_SPLITS),
        "--train", "0.8",
        "--val", "0.1",
        "--test", "0.1",
    ])

    print("\n=== 6. Train TF-IDF + LogReg ===")
    tfidf_output = MODELS_DIR / "tfidf_seniority"
    run_cmd([
        sys.executable,
        str(SCRIPT_DIR / "train_tfidf.py"),
        "--splits-dir", str(DATA_SPLITS),
        "--output-dir", str(tfidf_output),
    ])

    # Load TF-IDF metrics
    metrics_path = tfidf_output / "tfidf_metrics.json"
    with open(metrics_path, encoding="utf-8") as f:
        metrics = json.load(f)
    acc = metrics["accuracy"]

    print(f"\n  TF-IDF accuracy: {acc:.4f} (target: {args.target_acc})")

    if acc >= args.target_acc:
        print("\n  SUCCESS: Target accuracy reached with TF-IDF + LogReg!")
        print(f"  Model: {tfidf_output}")
        return

    print("\n=== 7. TF-IDF < target. Trying DistilBERT... ===")
    try:
        run_cmd([
            sys.executable,
            str(ML_ROOT / "training" / "train.py"),
            "--task", "seniority",
            "--language_mode", "mono",
            "--languages", "pt-BR",
            "--base_model", "neuralmind/bert-base-portuguese-cased",  # BERTimbau (no DistilBERT pt easily)
            "--splits_dir", str(DATA_SPLITS),
            "--output_dir", str(MODELS_DIR),
            "--reports_dir", str(REPORTS_DIR),
        ], cwd=str(ML_ROOT / "training"))
    except Exception as e:
        print(f"  BERT training failed (GPU/memory?): {e}")
        print("  Consider: pip install torch transformers")
        print(f"  TF-IDF model remains at {tfidf_output} with acc={acc:.4f}")
        return

    # Check BERT report for accuracy
    reports_dirs = list(REPORTS_DIR.glob("analysis_*"))
    if reports_dirs:
        latest = max(reports_dirs, key=lambda p: p.stat().st_mtime)
        cost_path = latest / "training_cost.md"
        if cost_path.exists():
            content = cost_path.read_text(encoding="utf-8")
            if "accuracy" in content:
                # Parse accuracy from report
                for line in content.splitlines():
                    if "accuracy" in line.lower():
                        print(f"  {line.strip()}")
    print(f"\n  Pipeline done. TF-IDF acc={acc:.4f}. Check {REPORTS_DIR} for BERT results.")


if __name__ == "__main__":
    main()
