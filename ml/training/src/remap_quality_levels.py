"""
Collapse quality labels from 4 classes to 3 classes (poor/ok/strong).

Usage:
  python ml/training/src/remap_quality_levels.py
"""
from __future__ import annotations

import json
from pathlib import Path


def normalize_quality_level(level: str | None, score: int | float | None) -> str:
    level_norm = str(level or "").strip().lower()
    if level_norm == "poor":
        return "poor"
    if level_norm == "ok":
        return "ok"
    if level_norm in {"good", "excellent", "strong"}:
        return "strong"
    score = float(score or 0)
    if score < 40:
        return "poor"
    if score < 60:
        return "ok"
    return "strong"


def rewrite_file(path: Path) -> None:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        labels = record.setdefault("labels", {})
        labels["quality_level"] = normalize_quality_level(labels.get("quality_level"), labels.get("quality_score"))
        rows.append(json.dumps(record, ensure_ascii=False))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    splits_dir = Path(__file__).resolve().parents[2] / "data" / "splits"
    for filename in ("train.jsonl", "val.jsonl", "test.jsonl"):
        path = splits_dir / filename
        if path.exists():
            rewrite_file(path)
            print(f"Updated {path}")


if __name__ == "__main__":
    main()
