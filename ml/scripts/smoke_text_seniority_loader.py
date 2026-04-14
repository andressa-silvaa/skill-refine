#!/usr/bin/env python3
"""
Smoke: load text seniority bundle from disk (ANALYSIS_TEXT_SENIORITY_MODEL_DIR) and run 2 predictions.

Does not start the web app. Set env before Django imports (this script does that).

Usage (repo root):
  python ml/scripts/smoke_text_seniority_loader.py
  python ml/scripts/smoke_text_seniority_loader.py --model-dir /mnt/c/Skill-Refine-TCC/ml/models/text_seniority_v1
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--model-dir",
        type=Path,
        default=repo / "ml" / "models" / "text_seniority_v1",
        help="Path to HF export (same as ANALYSIS_TEXT_SENIORITY_MODEL_DIR).",
    )
    args = ap.parse_args()
    model_dir = args.model_dir.resolve()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ["ANALYSIS_TEXT_SENIORITY_ENABLED"] = "true"
    os.environ["ANALYSIS_TEXT_SENIORITY_MODEL_DIR"] = str(model_dir)

    backend_src = repo / "backend" / "src"
    if str(backend_src) not in sys.path:
        sys.path.insert(0, str(backend_src))

    import django

    django.setup()

    from django.conf import settings

    from apps.analysis.application.inference.text_seniority.loader_text_seniority_model import (
        clear_text_seniority_cache,
        get_text_seniority_bundle,
    )
    from apps.analysis.application.inference.text_seniority.predict import predict_text_seniority

    clear_text_seniority_cache()
    bundle = get_text_seniority_bundle(settings)
    if not bundle or not bundle.get("model"):
        print("FAIL: bundle not loaded. Check ANALYSIS_TEXT_SENIORITY_MODEL_DIR and transformers/torch.", file=sys.stderr)
        return 1

    meta = bundle.get("metadata") or {}
    version = meta.get("model_version", "?")
    provider = meta.get("provider", "?")

    samples = [
        ("desenvolvedor sênior com 10 anos de experiência, líder técnico de equipe", "strong_senior"),
        ("estudante", "weak"),
    ]
    for text, tag in samples:
        r = predict_text_seniority(text, "pt-BR", bundle, allow_lexical_fallback=False)
        print(f"[{tag}]")
        print(f"  label:       {r.get('label')}")
        print(f"  confidence:  {r.get('confidence')}")
        print(f"  source:      {r.get('source')}")
        print(f"  model_version: {version}")
        print(f"  provider:      {provider}")
        probs = r.get("probs") or {}
        if probs:
            top = sorted(probs.items(), key=lambda x: -x[1])[:4]
            print(f"  probs (top): {top}")
        print()

    print("OK: neural text seniority path loaded (not heuristics-only for this loader).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
