"""
Full pipeline for multi-language training: generate PT+EN+ES -> preprocess -> label -> split -> train.
Target: accuracy >= 0.9 per language (pt-BR, en-US, es-ES). Uses XLM-R and more data/epochs.
Run from repo root: python ml/scripts/run_full_pipeline_multilang.py
Or from ml/scripts: python run_full_pipeline_multilang.py
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
TRAINING_DIR = ML_ROOT / "training"

# Config: more data and epochs for >= 90% accuracy per language
PER_LANG_COUNT = 1000
EPOCHS = 20
BATCH_SIZE = 16
BASE_MODEL = "xlm-roberta-base"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("RUN:", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd or SCRIPT_DIR)
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def main() -> None:
    py = sys.executable
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    DATA_SPLITS.mkdir(parents=True, exist_ok=True)

    # 1) Generate synthetic resumes per language
    for lang in ("pt", "en", "es"):
        run([
            py, str(SCRIPT_DIR / "generate_synthetic_resumes.py"),
            "-n", str(PER_LANG_COUNT),
            "--language", lang,
            "-o", str(DATA_RAW / f"synthetic_{lang}.jsonl"),
        ])

    # 2) Merge into one JSONL
    all_path = DATA_RAW / "synthetic_all.jsonl"
    with open(all_path, "w", encoding="utf-8") as fout:
        for lang in ("pt", "en", "es"):
            p = DATA_RAW / f"synthetic_{lang}.jsonl"
            for line in open(p, encoding="utf-8"):
                line = line.strip()
                if line:
                    fout.write(line + "\n")
    print(f"Merged -> {all_path}", flush=True)

    # 3) Preprocess
    run([
        py, str(SCRIPT_DIR / "preprocess.py"),
        str(all_path),
        "-o", str(DATA_PROCESSED / "preprocessed.jsonl"),
    ])

    # 4) Label with heuristics
    run([
        py, str(SCRIPT_DIR / "label_with_heuristics.py"),
        str(DATA_PROCESSED / "preprocessed.jsonl"),
        "-o", str(DATA_PROCESSED / "labeled.jsonl"),
    ])

    # 5) Split by resume_id (80/10/10)
    run([
        py, str(SCRIPT_DIR / "split_by_resume_id.py"),
        str(DATA_PROCESSED / "labeled.jsonl"),
        "-o", str(DATA_SPLITS),
        "--train", "0.8", "--val", "0.1", "--test", "0.1",
    ])

    # 6) Train multi-language (XLM-R, all 3 languages)
    run([
        py, str(TRAINING_DIR / "train.py"),
        "--task", "seniority",
        "--language_mode", "multi",
        "--languages", "pt-BR", "en-US", "es-ES",
        "--base_model", BASE_MODEL,
        "--epochs", str(EPOCHS),
        "--batch_size", str(BATCH_SIZE),
        "--splits_dir", str(DATA_SPLITS),
        "--output_dir", str(ML_ROOT / "models"),
        "--reports_dir", str(ML_ROOT / "reports"),
    ], cwd=str(TRAINING_DIR))

    print("Pipeline done. Check ml/reports/<model_version>/ for per-language accuracy.", flush=True)


if __name__ == "__main__":
    main()
