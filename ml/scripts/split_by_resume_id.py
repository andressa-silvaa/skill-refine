"""
Split dataset by resume_id to avoid leakage: all rows with the same resume_id
go to the same split (train/val/test). Stratify by language when possible.
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

DEFAULT_TRAIN = 0.8
DEFAULT_VAL = 0.1
DEFAULT_TEST = 0.1
LANGUAGES = ("pt", "en", "es")


def collect_resume_ids(rows: list[dict]) -> dict[str, list[dict]]:
    """Group rows by resume_id. Rows without resume_id get a synthetic id per row."""
    by_id: dict[str, list[dict]] = defaultdict(list)
    for i, row in enumerate(rows):
        rid = row.get("resume_id") or f"_single_{i}"
        by_id[rid].append(row)
    return dict(by_id)


def _get_stratify_key(rows: list[dict], resume_id: str) -> str:
    """Key for stratification: language + seniority (or language only)."""
    row = rows[0] if rows else {}
    lang = (row.get("language") or "pt").replace("-BR", "").replace("-US", "").replace("-ES", "")
    labels = row.get("labels") or {}
    seniority = labels.get("seniority") or "mid"
    return f"{lang}_{seniority}"


def split_ids(
    resume_ids: list[str],
    by_resume: dict[str, list[dict]],
    *,
    train_ratio: float = DEFAULT_TRAIN,
    val_ratio: float = DEFAULT_VAL,
    test_ratio: float = DEFAULT_TEST,
    seed: int = 42,
    stratify: bool = True,
) -> tuple[list[str], list[str], list[str]]:
    """Return (train_ids, val_ids, test_ids). If stratify, split per stratum (language_seniority)."""
    rng = random.Random(seed)
    if not stratify or not by_resume:
        ids = list(resume_ids)
        rng.shuffle(ids)
        n = len(ids)
        if n == 0:
            return [], [], []
        t = int(n * train_ratio)
        v = int(n * val_ratio)
        return ids[:t], ids[t : t + v], ids[t + v :]
    strata: dict[str, list[str]] = defaultdict(list)
    for rid in resume_ids:
        key = _get_stratify_key(by_resume[rid], rid)
        strata[key].append(rid)
    train_ids, val_ids, test_ids = [], [], []
    for stratum_ids in strata.values():
        rng.shuffle(stratum_ids)
        n = len(stratum_ids)
        t = max(0, int(n * train_ratio))
        v = max(0, int(n * val_ratio))
        train_ids.extend(stratum_ids[:t])
        val_ids.extend(stratum_ids[t : t + v])
        test_ids.extend(stratum_ids[t + v :])
    rng.shuffle(train_ids)
    rng.shuffle(val_ids)
    rng.shuffle(test_ids)
    return train_ids, val_ids, test_ids


def run(
    input_path: Path,
    output_dir: Path,
    *,
    train_ratio: float = DEFAULT_TRAIN,
    val_ratio: float = DEFAULT_VAL,
    test_ratio: float = DEFAULT_TEST,
    seed: int = 42,
    stratify: bool = True,
) -> None:
    """Read JSONL from input_path, split by resume_id (stratified by language+seniority when possible), write train/val/test JSONL."""
    rows: list[dict] = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    by_resume = collect_resume_ids(rows)
    resume_ids = list(by_resume.keys())
    train_ids, val_ids, test_ids = split_ids(
        resume_ids,
        by_resume,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        seed=seed,
        stratify=stratify,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    def write_split(name: str, ids: list[str]) -> None:
        out_rows: list[dict] = []
        for rid in ids:
            out_rows.extend(by_resume[rid])
        path = output_dir / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for row in out_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_split("train", train_ids)
    write_split("val", val_ids)
    write_split("test", test_ids)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Split dataset by resume_id (no leakage)")
    p.add_argument("input", type=Path, help="Input JSONL path (processed dataset)")
    p.add_argument("-o", "--output-dir", type=Path, default=Path("data/splits"), help="Output directory")
    p.add_argument("--train", type=float, default=DEFAULT_TRAIN)
    p.add_argument("--val", type=float, default=DEFAULT_VAL)
    p.add_argument("--test", type=float, default=DEFAULT_TEST)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-stratify", action="store_true", help="Disable stratification by language+seniority")
    args = p.parse_args()
    run(
        args.input,
        args.output_dir,
        train_ratio=args.train,
        val_ratio=args.val,
        test_ratio=args.test,
        seed=args.seed,
        stratify=not args.no_stratify,
    )


if __name__ == "__main__":
    main()
