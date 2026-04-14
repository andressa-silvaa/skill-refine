from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.infrastructure.models import User
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume, ResumeStatus


class DashboardAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/dashboard/summary"
        self.user_a, _ = User.objects.get_or_create(
            email="dashboard-a@test.local",
            defaults={"full_name": "User A", "status": "active"},
        )
        self.user_b, _ = User.objects.get_or_create(
            email="dashboard-b@test.local",
            defaults={"full_name": "User B", "status": "active"},
        )

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_returns_real_metrics_and_user_ownership(self):
        resume_a1 = Resume.objects.create(
            user_id=self.user_a.id,
            name="Backend Resume",
            status=ResumeStatus.COMPLETE,
            score=71,
        )
        resume_a2 = Resume.objects.create(
            user_id=self.user_a.id,
            name="Frontend Resume",
            status=ResumeStatus.DRAFT,
        )
        Resume.objects.create(
            user_id=self.user_a.id,
            name="Data Resume",
            status=ResumeStatus.COMPLETE,
        )
        Resume.objects.create(
            user_id=self.user_b.id,
            name="Other User Resume",
            status=ResumeStatus.COMPLETE,
            score=99,
        )

        first_analysis = ResumeAnalysis.objects.create(
            user_id=self.user_a.id,
            resume_id=resume_a1.id,
            status=AnalysisStatus.DONE,
            score=60,
            task_scores={"ats": 60, "clarity": 65, "seniority": 55, "matching": 58},
            resume_content_synced_at=resume_a1.updated_at,
            payload_json={
                "insights": {
                    "improvements": [
                        {"key": "analysis.insights.improvements.ats_keywords", "priority": "high"},
                        {"key": "analysis.insights.improvements.add_metrics", "priority": "high"},
                    ]
                }
            },
        )
        first_analysis.created_at = timezone.now() - timedelta(days=40)
        first_analysis.save(update_fields=["created_at"])

        second_analysis = ResumeAnalysis.objects.create(
            user_id=self.user_a.id,
            resume_id=resume_a2.id,
            status=AnalysisStatus.DONE,
            score=80,
            task_scores={"ats": 82, "clarity": 78, "seniority": 74, "matching": 76},
            resume_content_synced_at=resume_a2.updated_at,
            payload_json={
                "insights": {
                    "improvements": [
                        {"key": "analysis.insights.improvements.ats_keywords", "priority": "medium"},
                        {"key": "analysis.insights.improvements.improve_summary", "priority": "medium"},
                    ]
                }
            },
        )
        second_analysis.created_at = timezone.now() - timedelta(days=3)
        second_analysis.save(update_fields=["created_at"])

        resume_other = Resume.objects.filter(user_id=self.user_b.id).first()
        ResumeAnalysis.objects.create(
            user_id=self.user_b.id,
            resume_id=resume_other.id,
            status=AnalysisStatus.DONE,
            score=95,
            task_scores={"ats": 95, "clarity": 95, "seniority": 95},
            resume_content_synced_at=resume_other.updated_at,
            payload_json={"insights": {"improvements": [{"key": "analysis.insights.improvements.other"}]}},
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()

        summary = body["summary"]
        self.assertEqual(summary["totalResumes"], 3)
        self.assertEqual(summary["completeResumes"], 2)
        self.assertEqual(summary["draftResumes"], 1)
        self.assertEqual(summary["lastAnalyzedResumeId"], str(resume_a2.id))
        self.assertEqual(summary["lastAnalyzedResumeTitle"], "Frontend Resume")
        self.assertEqual(summary["averageScore"], 70)
        self.assertEqual(summary["pendingSuggestions"], 4)
        self.assertEqual(summary["highPrioritySuggestions"], 2)

        recent_titles = [item["name"] for item in body["recentResumes"]]
        self.assertTrue(any(title == "Frontend Resume" for title in recent_titles))
        self.assertFalse(any(title == "Other User Resume" for title in recent_titles))

        self.assertTrue(len(body["scoreEvolution"]) >= 1)
        self.assertEqual(len(body["competencies"]), 6)

        insights = body["aiInsights"]
        self.assertGreaterEqual(len(insights), 1)
        self.assertEqual(insights[0]["key"], "analysis.insights.improvements.ats_keywords")
        self.assertEqual(insights[0]["count"], 2)

    def test_empty_state_when_user_has_no_resumes(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["summary"]["totalResumes"], 0)
        self.assertEqual(body["summary"]["completeResumes"], 0)
        self.assertEqual(body["summary"]["draftResumes"], 0)
        self.assertIsNone(body["summary"]["averageScore"])
        self.assertEqual(body["recentResumes"], [])
        self.assertEqual(body["aiInsights"], [])

