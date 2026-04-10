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

from apps.analysis.application.dataset_export import write_seniority_export_jsonl
from apps.analysis.application.internal_review import resolve_review_hash_salt


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
            help="ISO date/datetime (inclusive), e.g. 2025-01-01 or 2025-01-01T00:00:00",
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

    def handle(self, *args, **options):
        out = Path(options["out"]).expanduser()
        since_raw = options.get("since")
        since_dt: datetime | None = None
        if since_raw:
            try:
                since_dt = datetime.fromisoformat(since_raw.replace("Z", "+00:00"))
            except ValueError as exc:
                raise CommandError(f"Invalid --since: {since_raw}") from exc

        out.parent.mkdir(parents=True, exist_ok=True)
        salt = (options.get("hash_salt") or "").strip() or resolve_review_hash_salt()
        n = write_seniority_export_jsonl(
            str(out),
            limit=options.get("limit"),
            since=since_dt,
            mode=options["mode"],
            id_hash_salt=salt,
        )
        self.stdout.write(self.style.SUCCESS(f"Wrote {n} rows to {out}"))
