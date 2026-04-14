"""
Export seniority calibration / training rows from the database (JSONL).

Default mode is signals-only (no resume body). Use --mode full for redacted+capped text.

Comando oficial (a partir de ``backend/``):

  python manage.py export_seniority_dataset \\
    --out ../ml/data/processed/seniority_from_db.jsonl \\
    --limit 5000
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.analysis.application.dataset_export import DATASET_SCHEMA_VERSION, write_seniority_export_jsonl
from apps.analysis.application.internal_review import resolve_review_hash_salt

from .export_seniority_dataset_helpers import parse_since_argument


class Command(BaseCommand):
    help = "Export completed analyses as JSONL (signals + labels; optional sanitized text)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            type=str,
            required=True,
            help="Output path (JSONL).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Max rows (most recent first).",
        )
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="ISO date/datetime (inclusive) or relative window: 90d, 12w, 6m (UTC).",
        )
        parser.add_argument(
            "--mode",
            type=str,
            choices=("signals", "full"),
            default="signals",
            help="signals: structured only; full: add text_sanitized (PII-redacted, capped).",
        )
        parser.add_argument(
            "--hash-salt",
            type=str,
            default="",
            help="Salt for pseudo-keys (default: ANALYSIS_INTERNAL_REVIEW_KEY_SALT or SECRET_KEY prefix).",
        )
        parser.add_argument(
            "--schema-version",
            type=str,
            default=DATASET_SCHEMA_VERSION,
            help="Dataset schema_version written per row (default: project default, e.g. 1.1).",
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
        schema_ver = (options.get("schema_version") or DATASET_SCHEMA_VERSION).strip()
        n = write_seniority_export_jsonl(
            str(out),
            limit=options.get("limit"),
            since=since_dt,
            mode=options["mode"],
            id_hash_salt=salt,
            schema_version=schema_ver,
        )
        self.stdout.write(self.style.SUCCESS(f"Wrote {n} rows to {out}"))
