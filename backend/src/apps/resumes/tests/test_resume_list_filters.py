from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.infrastructure.models import User
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume, ResumeStatus


class ResumeListFiltersTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/resumes/api/resumes"
        self.user_a, _ = User.objects.get_or_create(
            email="resume-filters-a@test.local",
            defaults={"full_name": "User A", "status": "active"},
        )
        self.user_b, _ = User.objects.get_or_create(
            email="resume-filters-b@test.local",
            defaults={"full_name": "User B", "status": "active"},
        )
        self.client.force_authenticate(user=self.user_a)

        self.resume_draft = Resume.objects.create(
            user_id=self.user_a.id,
            name="Backend Draft",
            status=ResumeStatus.DRAFT,
            score=None,
        )
        self.resume_complete_low = Resume.objects.create(
            user_id=self.user_a.id,
            name="Frontend Low Score",
            status=ResumeStatus.COMPLETE,
            score=48,
        )
        self.resume_complete_high = Resume.objects.create(
            user_id=self.user_a.id,
            name="Data Engineer High",
            status=ResumeStatus.COMPLETE,
            score=92,
        )
        self.resume_analyzing = Resume.objects.create(
            user_id=self.user_a.id,
            name="AI Analyze",
            status=ResumeStatus.ANALYZING,
            score=70,
        )
        Resume.objects.create(
            user_id=self.user_b.id,
            name="Other User Hidden",
            status=ResumeStatus.COMPLETE,
            score=99,
        )

        old_date = timezone.now() - timedelta(days=45)
        Resume.objects.filter(id=self.resume_complete_low.id).update(updated_at=old_date)
        self.resume_complete_low.refresh_from_db()

    def _names(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [item["name"] for item in response.json()["items"]]

    def test_filter_by_status(self):
        response = self.client.get(self.url, {"status": "complete"})
        names = self._names(response)
        self.assertIn("Frontend Low Score", names)
        self.assertIn("Data Engineer High", names)
        self.assertNotIn("Backend Draft", names)

    def test_filter_by_score_range(self):
        ResumeAnalysis.objects.create(
            user_id=self.user_a.id,
            resume_id=self.resume_draft.id,
            status=AnalysisStatus.DONE,
            score=88,
        )
        response = self.client.get(self.url, {"score_min": "86", "score_max": "100"})
        names = self._names(response)
        self.assertIn("Data Engineer High", names)
        self.assertIn("Backend Draft", names)

    def test_filter_without_score(self):
        response = self.client.get(self.url, {"include_no_score": "true"})
        names = self._names(response)
        self.assertEqual(names, ["Backend Draft"])

    def test_filter_by_updated_from(self):
        updated_from = (timezone.now() - timedelta(days=7)).date().isoformat()
        response = self.client.get(self.url, {"updated_from": updated_from})
        names = self._names(response)
        self.assertIn("Backend Draft", names)
        self.assertIn("Data Engineer High", names)
        self.assertIn("AI Analyze", names)
        self.assertNotIn("Frontend Low Score", names)

    def test_combine_filters_and_search_with_ownership(self):
        response = self.client.get(
            self.url,
            {"status": "complete", "score_min": "80", "search": "Engineer"},
        )
        names = self._names(response)
        self.assertEqual(names, ["Data Engineer High"])
        self.assertNotIn("Other User Hidden", names)

