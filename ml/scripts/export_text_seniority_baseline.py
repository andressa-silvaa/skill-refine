#!/usr/bin/env python3
"""
Export a local Hugging Face bundle for text seniority (baseline, untrained classification head).

Default: neuralmind/bert-base-portuguese-cased + 4-class head (intern, junior, mid, senior).
Next step (TCC): fine-tune with gold labels (e.g. seniority_review_label) using the existing pipeline.

Usage (repo root, WSL):
  python ml/scripts/export_text_seniority_baseline.py \\
    --out ml/models/text_seniority_v1 \\
    --base neuralmind/bert-base-portuguese-cased
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _prepare_out_dir(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Export baseline text_seniority HF bundle (local disk).")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("ml/models/text_seniority_v1"),
        help="Output directory (created clean).",
    )
    ap.add_argument("--base", default="neuralmind/bert-base-portuguese-cased", help="HF model id for weights+tokenizer.")
    ap.add_argument(
        "--labels",
        nargs="+",
        default=["intern", "junior", "mid", "senior"],
        help="Class labels in id order (default: intern junior mid senior).",
    )
    args = ap.parse_args()

    labels = [str(x).strip().lower() for x in args.labels]
    if len(labels) != len(set(labels)):
        print("error: duplicate labels", file=sys.stderr)
        return 1

    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as e:
        print("error: install transformers and torch:", e, file=sys.stderr)
        return 1

    out: Path = args.out.resolve()
    _prepare_out_dir(out)

    id2label = {i: lab for i, lab in enumerate(labels)}
    label2id = {lab: i for i, lab in enumerate(labels)}

    tokenizer = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base,
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id,
    )

    # Prefer safetensors when the stack supports it.
    try:
        model.save_pretrained(str(out), safe_serialization=True)
    except TypeError:
        model.save_pretrained(str(out))
    tokenizer.save_pretrained(str(out))

    trained_at = _utc_now_iso()
    exported_at = _utc_now_iso()
    meta = {
        "schema_version": "1.0",
        "task": "text_seniority",
        "model_name": "text_seniority",
        "model_name_base": args.base,
        "model_version": "text_seniority_v1",
        "dataset_version": "baseline_untrained",
        "provider": "hf_local",
        "languages_supported": ["pt-BR"],
        "labels": labels,
        "classes": labels,
        "trained_at": trained_at,
        "exported_at": exported_at,
        "notes": "baseline head (untrained) - to be fine-tuned using gold labels",
        "metrics_summary": {
            "status": "baseline_zero_shot_head",
            "num_labels": len(labels),
        },
    }
    meta_path = out / "metadata.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote bundle to {out}")
    print(f"  metadata: {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
