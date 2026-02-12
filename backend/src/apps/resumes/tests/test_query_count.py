"""
Test that measures query count for list and detail (for N+1 fix verification).
Run: python manage.py test apps.resumes.tests.test_query_count -v 2
"""
from __future__ import annotations

from django.test import TestCase, override_settings

from apps.accounts.infrastructure.models import User
from apps.resumes.infrastructure.models import (
    Resume,
    ResumeContact,
    ResumeEducation,
    ResumeExperience,
    ResumeExperienceBullet,
    ResumeLanguage,
    ResumeSkill,
    ResumeStatus,
    ResumeTag,
)


@override_settings(DEBUG=True)
class ResumeQueryCountTest(TestCase):
    """Measure query count for list and detail endpoints."""

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            email="measure-queries@test.local",
            defaults={"full_name": "Measure User", "status": "active"},
        )
        self.resumes = list(
            Resume.objects.filter(user_id=self.user.id, deleted_at__isnull=True).order_by("-updated_at")
        )
        if len(self.resumes) < 2:
            for i in range(2 - len(self.resumes)):
                r = Resume.objects.create(
                    user_id=self.user.id,
                    name=f"Resume {i}",
                    status=ResumeStatus.DRAFT,
                    target_position="Dev",
                )
                ResumeTag.objects.get_or_create(resume=r, defaults={"label": f"T{r.id}", "position_index": 0})
                ResumeSkill.objects.get_or_create(resume=r, defaults={"name": "Python", "position_index": 0})
                ResumeContact.objects.get_or_create(resume=r, defaults={"full_name": "A", "email": "a@b.com"})
                exp = ResumeExperience.objects.create(resume=r, company="C", position="P", position_index=0)
                ResumeExperienceBullet.objects.create(experience=exp, content="X", position_index=0)
                ResumeEducation.objects.create(resume=r, institution="U", course="CS", position_index=0)
                ResumeLanguage.objects.create(resume=r, name="EN", level="intermediate", position_index=0)
                self.resumes.insert(0, r)
        self.detail_resume = self.resumes[0]

    def test_list_query_count(self):
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.user)
        # After N+1 fix: 3 queries (1 list + 2 prefetches for tags/skills). Before: 1 + 2*N.
        with self.assertNumQueries(3):
            api.get("/resumes/api/resumes")

    def test_detail_query_count(self):
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.user)
        # After N+1 fix: 6 queries (1 resume+contact, 5 prefetches: exp, bullets, edu, skills, lang).
        # Before fix: 1 + 1 contact + 4 + N_exp bullets = 6+ queries with N+1 per experience.
        with self.assertNumQueries(6):
            api.get(f"/resumes/api/resumes/{self.detail_resume.id}")
