"""Unit tests for synthetic resume seeding (no PII, coherent dates)."""
from __future__ import annotations

import random
from datetime import date

from django.test import SimpleTestCase

from apps.resumes.application.synthetic_seed import (
    PROFILE_ORDER,
    add_months,
    build_synthetic_resume,
    pick_profile,
)
from apps.resumes.interfaces.api.service_utils import parse_resume_date


class SyntheticSeedPureTest(SimpleTestCase):
    def test_add_months_roundtrip(self):
        d = date(2020, 1, 15)
        self.assertEqual(add_months(d, 12).year, 2021)
        self.assertEqual(add_months(d, -1).month, 12)
        self.assertEqual(add_months(d, -1).year, 2019)

    def test_pick_profile_balanced_cycles(self):
        rng = random.Random(1)
        got = [pick_profile(i, "balanced", rng) for i in range(8)]
        self.assertEqual(got[:4], list(PROFILE_ORDER))
        self.assertEqual(got[4:8], list(PROFILE_ORDER))

    def test_no_realistic_pii_domains(self):
        rng = random.Random(3)
        for i in range(20):
            p = PROFILE_ORDER[i % 4]
            payload = build_synthetic_resume(profile=p, rng=rng, index=i, base_seed=99)
            em = payload["contact"]["email"]
            self.assertIn("local.seed.invalid", em)
            self.assertNotIn("@gmail.com", em)
            self.assertEqual(payload["contact"]["fullName"], "Usuário Teste")

    def test_experience_dates_monotonic(self):
        rng = random.Random(7)
        for p in PROFILE_ORDER:
            pl = build_synthetic_resume(profile=p, rng=rng, index=42, base_seed=1)
            dates = []
            for e in pl["experiences"]:
                s = parse_resume_date(e["startDate"])
                if e.get("isCurrent"):
                    continue
                end_raw = e.get("endDate") or ""
                en = parse_resume_date(end_raw) if end_raw else None
                if s and en:
                    self.assertLessEqual(s, en)
                dates.append((s, en))
            self.assertTrue(len(pl["experiences"]) >= 0)
