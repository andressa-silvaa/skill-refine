"""
Tests for analysis API: auth, ownership, payload shape, run creates pending.
Run: python manage.py test apps.analysis.tests.test_analysis_api -v 2
"""
from __future__ import annotations

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.infrastructure.models import User
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.analysis.interfaces.api.payloads import analysis_payload
from apps.resumes.infrastructure.models import Resume, ResumeStatus


class AnalysisAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_a, _ = User.objects.get_or_create(
            email="analysis-test-a@test.local",
            defaults={"full_name": "User A", "status": "active"},
        )
        self.user_b, _ = User.objects.get_or_create(
            email="analysis-test-b@test.local",
            defaults={"full_name": "User B", "status": "active"},
        )
        self.resume_a = Resume.objects.create(
            user_id=self.user_a.id,
            name="Resume A",
            status=ResumeStatus.DRAFT,
            target_position="Dev",
        )
        self.resume_b = Resume.objects.create(
            user_id=self.user_b.id,
            name="Resume B",
            status=ResumeStatus.DRAFT,
            target_position="Dev",
        )
        self.run_url = "/analysis/run"
        self.latest_url = "/analysis/latest"
        self.history_url = "/analysis/history"


class TestRunRequiresAuth(AnalysisAPITestCase):
    def test_run_without_auth_returns_401(self):
        resp = self.client.post(
            self.run_url,
            {"resume_id": str(self.resume_a.id)},
            format="json",
        )
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class TestRunDeniesOtherUserResume(AnalysisAPITestCase):
    def test_run_with_other_user_resume_returns_404(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.post(
            self.run_url,
            {"resume_id": str(self.resume_b.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", resp.json() or {})


class TestLatestDeniesOtherUserResume(AnalysisAPITestCase):
    def test_latest_with_other_user_resume_returns_404(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(self.latest_url, {"resume_id": str(self.resume_b.id)})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class TestLatestBatch(AnalysisAPITestCase):
    def test_latest_batch_returns_only_owned_resume_items(self):
        ResumeAnalysis.objects.create(
            user_id=self.user_a.id,
            resume_id=self.resume_a.id,
            status=AnalysisStatus.DONE,
            score=77,
            task_scores={},
            payload_json={},
            model_name="m",
            model_version="v",
            provider="local",
        )
        ResumeAnalysis.objects.create(
            user_id=self.user_b.id,
            resume_id=self.resume_b.id,
            status=AnalysisStatus.DONE,
            score=99,
            task_scores={},
            payload_json={},
            model_name="m",
            model_version="v",
            provider="local",
        )

        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(
            self.latest_url,
            {"resume_ids": f"{self.resume_a.id},{self.resume_b.id}"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("items", data)
        self.assertIn(str(self.resume_a.id), data["items"])
        self.assertNotIn(str(self.resume_b.id), data["items"])


class TestRunCreatesPendingAnalysis(AnalysisAPITestCase):
    def test_run_creates_pending_and_returns_202(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.post(
            self.run_url,
            {"resume_id": str(self.resume_a.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["resumeId"], str(self.resume_a.id))
        self.assertEqual(ResumeAnalysis.objects.filter(resume_id=self.resume_a.id).count(), 1)
        analysis = ResumeAnalysis.objects.get(id=data["id"])
        self.assertEqual(analysis.status, AnalysisStatus.PENDING)


class TestPayloadShapeStable(AnalysisAPITestCase):
    def test_payload_shape_has_required_fields(self):
        analysis = ResumeAnalysis.objects.create(
            user_id=self.user_a.id,
            resume_id=self.resume_a.id,
            status=AnalysisStatus.DONE,
            score=85,
            task_scores={"ats": 92, "clarity": 78, "seniority": 0},
            payload_json={
                "insights": {
                    "strengths": [{"title": "Estrutura clara", "description": None}],
                    "improvements": [
                        {"title": "Adicionar métricas", "priority": "high", "description": None},
                    ],
                },
            },
            model_name="bertimbau-base",
            model_version="analysis_v1",
            provider="local",
        )
        payload = analysis_payload(analysis)
        self.assertIn("id", payload)
        self.assertIn("resumeId", payload)
        self.assertIn("status", payload)
        self.assertIn("score", payload)
        self.assertIn("taskScores", payload)
        self.assertIn("ats", payload["taskScores"])
        self.assertIn("clarity", payload["taskScores"])
        self.assertIn("seniority", payload["taskScores"])
        self.assertIn("insights", payload)
        self.assertIn("strengths", payload["insights"])
        self.assertIn("improvements", payload["insights"])
        self.assertIn("metadata", payload)
        self.assertIn("modelName", payload["metadata"])
        self.assertIn("modelVersion", payload["metadata"])
        self.assertIn("provider", payload["metadata"])
        self.assertIn("createdAt", payload)
        self.assertIn("updatedAt", payload)
        self.assertEqual(len(payload["insights"]["strengths"]), 1)
        self.assertIn("key", payload["insights"]["strengths"][0])
        self.assertEqual(
            payload["insights"]["strengths"][0].get("params", {}).get("title"),
            "Estrutura clara",
        )
        self.assertEqual(len(payload["insights"]["improvements"]), 1)
        self.assertEqual(payload["insights"]["improvements"][0]["priority"], "high")

    def test_failed_analysis_includes_error_message(self):
        analysis = ResumeAnalysis.objects.create(
            user_id=self.user_a.id,
            resume_id=self.resume_a.id,
            status=AnalysisStatus.FAILED,
            error_message="Mock error",
        )
        payload = analysis_payload(analysis)
        self.assertEqual(payload["status"], "failed")
        self.assertIn("errorMessage", payload)
        self.assertEqual(payload["errorMessage"], "Mock error")


class TestLatestRequiresAuth(AnalysisAPITestCase):
    def test_latest_without_auth_returns_401(self):
        resp = self.client.get(self.latest_url, {"resume_id": str(self.resume_a.id)})
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class TestHistoryRequiresAuth(AnalysisAPITestCase):
    def test_history_without_auth_returns_401(self):
        resp = self.client.get(self.history_url, {"resume_id": str(self.resume_a.id)})
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
