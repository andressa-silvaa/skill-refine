"""
Export target-fit JSONL (signals-only) for ML training.

  python manage.py export_target_fit_dataset \\
    --out ../ml/data/processed/target_fit_from_db.jsonl \\
    --limit 5000
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.analysis.application.dataset_export_target_fit import (
    TARGET_FIT_SCHEMA_VERSION,
    write_target_fit_export_jsonl,
)
from apps.analysis.application.internal_review import resolve_review_hash_salt

from .export_seniority_dataset_helpers import parse_since_argument


class Command(BaseCommand):
    help = "Export analyses with targetPosition as target-fit JSONL (signals-only, no PII text)."

    def add_arguments(self, parser):
        parser.add_argument("--out", type=str, required=True, help="Output path (JSONL).")
        parser.add_argument("--limit", type=int, default=None, help="Max analyses scanned (most recent first).")
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="ISO date/datetime (inclusive) or relative: 90d, 12w, 6m (UTC).",
        )
        parser.add_argument(
            "--schema-version",
            type=str,
            default=TARGET_FIT_SCHEMA_VERSION,
            help="schema_version written per row (default 1.0).",
        )
        parser.add_argument(
            "--label-source",
            type=str,
            choices=("policy", "review", "prefer-review"),
            default="policy",
            help="Label: policy heuristic, review-only, or prefer review when gold exists in payload.",
        )
        parser.add_argument(
            "--lang",
            type=str,
            default=None,
            help="If set, only rows whose user language preference matches (e.g. pt-BR).",
        )
        parser.add_argument(
            "--hash-salt",
            type=str,
            default="",
            help="Salt for pseudo-keys (default: ANALYSIS_INTERNAL_REVIEW_KEY_SALT or SECRET_KEY prefix).",
        )

    def handle(self, *args, **options):
        out = Path(options["out"]).expanduser()
        since_raw = options.get("since")
        since_dt: datetime | None = None
        if since_raw:
            try:
                since_dt = parse_since_argument(since_raw)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc

        out.parent.mkdir(parents=True, exist_ok=True)
        salt = (options.get("hash_salt") or "").strip() or resolve_review_hash_salt()
        schema_ver = (options.get("schema_version") or TARGET_FIT_SCHEMA_VERSION).strip()
        lang_opt = options.get("lang")
        lang_f = str(lang_opt).strip() if lang_opt else None

        n = write_target_fit_export_jsonl(
            str(out),
            limit=options.get("limit"),
            since=since_dt,
            id_hash_salt=salt,
            schema_version=schema_ver,
            label_source=options["label_source"],
            lang=lang_f,
        )
        self.stdout.write(self.style.SUCCESS(f"Wrote {n} rows to {out}"))
