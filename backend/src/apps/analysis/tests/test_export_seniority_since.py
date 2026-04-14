"""Tests for export_seniority_dataset --since relative parsing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from apps.analysis.management.commands.export_seniority_dataset_helpers import parse_since_argument


class ParseSinceArgumentTest(SimpleTestCase):
    def test_iso_date(self) -> None:
        dt = parse_since_argument("2025-06-01")
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 6)
        self.assertEqual(dt.day, 1)

    def test_relative_days(self) -> None:
        dt = parse_since_argument("90d")
        self.assertIsNotNone(dt)
        assert dt is not None
        now = datetime.now(timezone.utc)
        aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        delta = now - aware
        self.assertGreaterEqual(delta, timedelta(days=85))
        self.assertLessEqual(delta, timedelta(days=95))
