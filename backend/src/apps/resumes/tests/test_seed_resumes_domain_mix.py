"""seed_resumes --domain-mix balanced fills target_position and varies domains."""
from __future__ import annotations

import uuid

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.infrastructure.models import User, UserStatus
from apps.resumes.infrastructure.models import Resume


class SeedResumesDomainMixTest(TestCase):
    def test_domain_mix_sets_targets(self) -> None:
        email = f"seed-dom-{uuid.uuid4().hex[:10]}@local.seed.invalid"
        user = User.objects.create(email=email, full_name="Seed Dom", status=UserStatus.ACTIVE)
        call_command(
            "seed_resumes",
            user_email=email,
            count=12,
            seed=99,
            profiles="balanced",
            with_target_positions=True,
            domain_mix="balanced",
            tag="",
        )
        resumes = list(Resume.objects.filter(user_id=user.id))
        self.assertEqual(len(resumes), 12)
        titles = {r.target_position.strip() for r in resumes if r.target_position.strip()}
        self.assertGreaterEqual(len(titles), 3)
