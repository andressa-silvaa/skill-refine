#!/usr/bin/env python3
"""
Split target-fit JSONL by resume_key (no leakage). Same logic as seniority split.

  python ml/training/src/split_target_fit_dataset.py \\
    --in ml/data/processed/target_fit_from_db.jsonl \\
    --out_dir ml/data/splits/target_fit_v1 \\
    --seed 42
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap_backend_src() -> Path:
    root = Path(__file__).resolve().parents[3]
    src = root / "backend" / "src"
    if not (src / "apps" / "analysis").is_dir():
        print(f"Could not find Django apps under {src}", file=sys.stderr)
        sys.exit(1)
    sys.path.insert(0, str(src))
    return root


def main() -> int:
    _bootstrap_backend_src()
    from apps.analysis.application.dataset_resume_split import split_rows, write_split_jsonl

    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_path", required=True)
    p.add_argument("--out_dir", required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--train_ratio", type=float, default=0.7)
    p.add_argument("--val_ratio", type=float, default=0.15)
    args = p.parse_args()

    in_path = Path(args.in_path)
    rows: list[dict] = []
    with in_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    splits, _map, version = split_rows(
        rows,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
    )
    out_dir = Path(args.out_dir)
    write_split_jsonl(out_dir, splits, dataset_version=version)
    print(f"Wrote splits to {out_dir} (dataset_version={version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
