#!/usr/bin/env python3
"""
Thin wrapper: run Django management command export_seniority_dataset from repo root.

Usage (from repository root):
  python ml/scripts/export_seniority_from_db.py --out ml/data/processed/seniority_from_db.jsonl --limit 1000

Or pass any arguments supported by export_seniority_dataset.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"
    manage = backend / "manage.py"
    if not manage.is_file():
        print("Could not find backend/manage.py (run from Skill-Refine-TCC repo root).", file=sys.stderr)
        return 1
    cmd = [sys.executable, str(manage), "export_seniority_dataset", *sys.argv[1:]]
    return subprocess.call(cmd, cwd=str(backend))


if __name__ == "__main__":
    raise SystemExit(main())
