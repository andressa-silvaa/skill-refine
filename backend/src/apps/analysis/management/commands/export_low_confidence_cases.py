"""
Export low-confidence seniority analyses to dataset JSONL (default schema v1.1, signals-only).

Same row shape as ``export_seniority_dataset`` but filtered to a confidence tier.

Example:
  python manage.py export_low_confidence_cases --out ../ml/data/processed/low_confidence.jsonl --limit 500
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.analysis.application.dataset_export import DATASET_SCHEMA_VERSION, iter_dataset_rows_for_analyses
from apps.analysis.application.internal_review import (
    apply_internal_review_filters,
    base_done_queryset,
    filter_queryset_by_gating_reason,
    resolve_review_hash_salt,
)
_PREFETCH = (
    "resume__resumecontact",
    "resume__resumeexperience_set__resumeexperiencebullet_set",
    "resume__resumeeducation_set",
    "resume__resumeskill_set",
    "resume__resumelanguage_set",
)


class Command(BaseCommand):
    help = "Export low/medium/high-confidence seniority rows (JSONL, signals-only)."

    def add_arguments(self, parser):
        parser.add_argument("--out", type=str, required=True, help="Output JSONL path.")
        parser.add_argument(
            "--confidence",
            type=str,
            choices=("low", "medium", "high"),
            default="low",
            help="Filter payload seniorityConfidence (default: low).",
        )
        parser.add_argument("--limit", type=int, default=500, help="Max rows (default 500).")
        parser.add_argument(
            "--has-reason",
            type=str,
            default="",
            help="Optional exact gating reason code (e.g. no_experiences).",
        )
        parser.add_argument(
            "--hash-salt",
            type=str,
            default="",
            help="Salt for pseudo-keys (default from settings).",
        )
        parser.add_argument(
            "--schema-version",
            type=str,
            default=DATASET_SCHEMA_VERSION,
            help="Per-row schema_version (default: project default).",
        )

    def handle(self, *args, **options):
        out = Path(options["out"]).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        conf = options["confidence"]
        limit = max(1, min(int(options["limit"]), 50_000))
        salt = (options.get("hash_salt") or "").strip() or resolve_review_hash_salt()

        base = base_done_queryset().select_related("resume", "user").prefetch_related(*_PREFETCH)
        qs = apply_internal_review_filters(base, {}, confidence=conf)

        has_reason = (options.get("has_reason") or "").strip()
        if has_reason:
            analyses = filter_queryset_by_gating_reason(qs, has_reason, prefetch_limit=limit * 20)[:limit]
        else:
            analyses = list(qs[:limit])

        schema_ver = (options.get("schema_version") or DATASET_SCHEMA_VERSION).strip()
        count = 0
        with out.open("w", encoding="utf-8") as f:
            for row in iter_dataset_rows_for_analyses(
                analyses,
                hash_salt=salt,
                include_text=False,
                schema_version=schema_ver,
            ):
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Wrote {count} rows to {out}"))
