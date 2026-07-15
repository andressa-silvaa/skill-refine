"""
Freeze or compare golden analyze_resume() snapshots (refactoring safety net).

  # Write / refresh frozen baseline (only when intentionally updating):
  python manage.py compare_inference_snapshots --write-baseline

  # Compare current pipeline against frozen baseline (exit 1 on any field diff):
  python manage.py compare_inference_snapshots

  # Optional: write current run elsewhere for inspection
  python manage.py compare_inference_snapshots --write-current tmp/current.json
"""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.analysis.application.inference.snapshot.compare import (
    compare_snapshots,
    format_diff_report,
    load_snapshot,
)
from apps.analysis.application.inference.snapshot.runner import (
    assert_golden_case_count,
    default_baseline_path,
    run_golden_snapshots,
    write_snapshot,
)


class Command(BaseCommand):
    help = "Compare analyze_resume golden snapshots against a frozen baseline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--baseline",
            type=str,
            default="",
            help="Path to frozen baseline JSON (default: tests/golden_snapshots/baseline.json).",
        )
        parser.add_argument(
            "--write-baseline",
            action="store_true",
            dest="write_baseline",
            help="Regenerate and overwrite the frozen baseline from the current pipeline.",
        )
        parser.add_argument(
            "--write-current",
            type=str,
            default="",
            dest="write_current",
            help="Also write the current snapshot JSON to this path.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=80,
            help="Max divergences to print.",
        )

    def handle(self, *args, **options):
        assert_golden_case_count(30)
        baseline_path = Path(options["baseline"] or default_baseline_path())
        write_baseline = bool(options.get("write_baseline"))
        write_current = (options.get("write_current") or "").strip()
        limit = max(1, int(options["limit"]))

        self.stdout.write("Running golden snapshots (deterministic settings)...")
        current = run_golden_snapshots()
        self.stdout.write(f"Cases: {current['case_count']}")

        if write_current:
            out = write_snapshot(write_current, current)
            self.stdout.write(self.style.SUCCESS(f"Wrote current snapshot: {out}"))

        if write_baseline:
            out = write_snapshot(baseline_path, current)
            self.stdout.write(self.style.SUCCESS(f"Wrote baseline: {out}"))
            return

        if not baseline_path.is_file():
            raise CommandError(
                f"Baseline not found: {baseline_path}. "
                "Run with --write-baseline once to freeze the current pipeline."
            )

        baseline = load_snapshot(baseline_path)
        diffs = compare_snapshots(baseline, current)
        report = format_diff_report(diffs, limit=limit)
        if diffs:
            self.stderr.write(self.style.ERROR(report))
            raise CommandError(f"Golden snapshot comparison failed ({len(diffs)} divergences).")
        self.stdout.write(self.style.SUCCESS(report))
