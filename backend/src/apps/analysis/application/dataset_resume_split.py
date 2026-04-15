"""
Deterministic train/val/test split by resume_key (no row-level leakage).

Used by ``ml/training/src/split_dataset.py`` (monorepo). Pure Python / no ORM.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


def group_rows_by_resume_key(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(row.get("resume_key") or "").strip()
        if not key:
            continue
        buckets[key].append(row)
    return dict(buckets)


def _stable_key_sort(keys: list[str], *, seed: int) -> list[str]:
    def sort_key(k: str) -> tuple[bytes, str]:
        h = hashlib.sha256(f"{seed}:{k}".encode("utf-8")).digest()
        return (h, k)

    return sorted(keys, key=sort_key)


def assign_split_labels(resume_keys: list[str], *, seed: int, train_ratio: float, val_ratio: float) -> dict[str, str]:
    """
    Assign each resume_key to train | val | test. Mutually exclusive, exhaustive.
    """
    if train_ratio <= 0 or val_ratio <= 0 or train_ratio + val_ratio >= 1:
        raise ValueError("invalid ratios: need 0 < train, 0 < val, train+val < 1")
    test_ratio = 1.0 - train_ratio - val_ratio
    if test_ratio <= 0:
        raise ValueError("train_ratio + val_ratio must be < 1")

    ordered = _stable_key_sort(list(resume_keys), seed=seed)
    n = len(ordered)
    n_train = int(round(n * train_ratio))
    n_val = int(round(n * val_ratio))
    n_train = max(0, min(n_train, n))
    n_val = max(0, min(n_val, n - n_train))
    splits: dict[str, str] = {}
    for i, k in enumerate(ordered):
        if i < n_train:
            splits[k] = "train"
        elif i < n_train + n_val:
            splits[k] = "val"
        else:
            splits[k] = "test"
    return splits


def split_rows(
    rows: list[dict[str, Any]],
    *,
    seed: int = 42,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str], str]:
    """
    Returns (split_name -> rows, resume_key -> split_name, dataset_version fingerprint).
    """
    buckets = group_rows_by_resume_key(rows)
    if not buckets:
        return {"train": [], "val": [], "test": []}, {}, "empty"

    key_to_split = assign_split_labels(list(buckets.keys()), seed=seed, train_ratio=train_ratio, val_ratio=val_ratio)
    out: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    for rk, group in buckets.items():
        name = key_to_split.get(rk, "train")
        out.setdefault(name, []).extend(group)

    fingerprint = hashlib.sha256()
    fingerprint.update(f"seed={seed};train={train_ratio};val={val_ratio};".encode("utf-8"))
    for k in sorted(buckets.keys()):
        fingerprint.update(k.encode("utf-8"))
        fingerprint.update(str(len(buckets[k])).encode("utf-8"))
    version = fingerprint.hexdigest()[:24]
    return out, key_to_split, version


def write_split_jsonl(out_dir: Path, splits: dict[str, list[dict[str, Any]]], *, dataset_version: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "dataset_version": dataset_version,
        "splits": {k: len(v) for k, v in splits.items()},
    }
    (out_dir / "split_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    for name, rows in splits.items():
        path = out_dir / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
