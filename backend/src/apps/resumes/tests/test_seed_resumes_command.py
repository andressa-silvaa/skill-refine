"""Management command seed_resumes creates tagged synthetic resumes."""
from __future__ import annotations

import uuid

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.infrastructure.models import User
from apps.resumes.infrastructure.models import Resume, ResumeContact, ResumeTag


class SeedResumesCommandTest(TestCase):
    def test_creates_resumes_with_seed_tag_and_fake_email(self):
        email = f"seed-cmd-{uuid.uuid4().hex[:10]}@local.seed.invalid"
        call_command(
            "seed_resumes",
            user_email=email,
            count=3,
            seed=11,
            profiles="balanced",
            tag="seed_synthetic",
        )
        user = User.objects.get(email__iexact=email)
        resumes = list(Resume.objects.filter(user_id=user.id, deleted_at__isnull=True))
        self.assertEqual(len(resumes), 3)
        for r in resumes:
            self.assertTrue(r.name.startswith("Seed s11"))
            ct = ResumeContact.objects.get(resume=r)
            self.assertIn("local.seed.invalid", ct.email)
            tags = list(ResumeTag.objects.filter(resume=r).values_list("label", flat=True))
            self.assertIn("seed_synthetic", tags)
