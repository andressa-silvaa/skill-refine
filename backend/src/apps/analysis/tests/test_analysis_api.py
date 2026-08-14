"""
Tests for analysis API: auth, ownership, payload shape, run creates pending.
Run: python manage.py test apps.analysis.tests.test_analysis_api -v 2
"""
from __future__ import annotations

from unittest import mock

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.infrastructure.models import User
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.analysis.interfaces.api.payloads import analysis_payload
from apps.resumes.infrastructure.models import Resume, ResumeStatus


class AnalysisAPITestCase(TestCase):
    def _resume_content_synced_at(self, resume: Resume):
        """Snapshot timestamp to tie an analysis to the resume row (matches production run_analysis)."""
        resume.refresh_from_db()
        return resume.updated_at

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
            resume_content_synced_at=self._resume_content_synced_at(self.resume_a),
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
            resume_content_synced_at=self._resume_content_synced_at(self.resume_b),
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


class TestLatestInvalidatedAfterResumeEdit(AnalysisAPITestCase):
    """Análise concluída deixa de ser "latest" quando o currículo é salvo de novo."""

    def test_latest_returns_null_after_resume_change(self):
        ResumeAnalysis.objects.create(
            user_id=self.user_a.id,
            resume_id=self.resume_a.id,
            status=AnalysisStatus.DONE,
            score=90,
            task_scores={},
            payload_json={"insights": {"strengths": [], "improvements": []}},
            model_name="m",
            model_version="v",
            provider="local",
            resume_content_synced_at=self._resume_content_synced_at(self.resume_a),
        )
        self.client.force_authenticate(user=self.user_a)
        r1 = self.client.get(self.latest_url, {"resume_id": str(self.resume_a.id)})
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(r1.json().get("item"))

        self.resume_a.summary = "Conteúdo alterado após a análise."
        self.resume_a.save()

        r2 = self.client.get(self.latest_url, {"resume_id": str(self.resume_a.id)})
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertIsNone(r2.json().get("item"))

    def test_latest_batch_omits_stale_analysis(self):
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
            resume_content_synced_at=self._resume_content_synced_at(self.resume_a),
        )
        self.resume_a.target_position = "Novo cargo"
        self.resume_a.save()

        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(
            self.latest_url,
            {"resume_ids": str(self.resume_a.id)},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        items = resp.json().get("items") or {}
        self.assertEqual(items, {})


class TestRunCreatesPendingAnalysis(AnalysisAPITestCase):
    """
    The API contract for POST /run: a pending row exists and 202 comes back. Not the worker.

    The dispatch is stubbed because ``run_resume_analysis_task`` opens with ``connection.close()``.
    That is right for a Celery worker process, which should drop a possibly-stale connection before
    it starts, but the task runs inline here, so it closed the connection this test was using and
    every assertion below failed with "the connection is closed". What the worker does has its own
    suites (``test_worker``, ``test_batch_run_analysis``).
    """

    def test_run_creates_pending_and_returns_202(self):
        self.client.force_authenticate(user=self.user_a)
        with mock.patch(
            "apps.analysis.interfaces.api.services.run_resume_analysis_task"
        ) as dispatch:
            resp = self.client.post(
                self.run_url,
                {"resume_id": str(self.resume_a.id)},
                format="json",
            )
        self.assertEqual(dispatch.delay.call_count, 1)
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        data = resp.json()
        self.assertIn("id", data)
        self.assertIn(data["status"], ("pending", "running", "done"))
        self.assertEqual(data["resumeId"], str(self.resume_a.id))
        self.assertEqual(ResumeAnalysis.objects.filter(resume_id=self.resume_a.id).count(), 1)
        analysis = ResumeAnalysis.objects.get(id=data["id"])
        self.assertIn(analysis.status, (AnalysisStatus.PENDING, AnalysisStatus.RUNNING, AnalysisStatus.DONE))


class TestPayloadShapeStable(AnalysisAPITestCase):
    def test_payload_shape_has_required_fields(self):
        analysis = ResumeAnalysis.objects.create(
            user_id=self.user_a.id,
            resume_id=self.resume_a.id,
            status=AnalysisStatus.DONE,
            score=85,
            task_scores={"ats": 92, "clarity": 78, "seniority": 0},
            resume_content_synced_at=self._resume_content_synced_at(self.resume_a),
            payload_json={
                "insights": {
                    "strengths": [{"key": "analysis.insights.strengths.clear_structure", "params": {}}],
                    "improvements": [
                        {"title": "Adicionar métricas", "priority": "high", "description": None},
                    ],
                },
                "model_metadata_by_task": {
                    "seniority": {
                        "modelName": "neuralmind/bert-base-portuguese-cased",
                        "modelVersion": "analysis_v1_pt",
                        "datasetVersion": "abc123",
                        "provider": "local",
                    },
                    "quality": {
                        "modelName": "neuralmind/bert-base-portuguese-cased",
                        "modelVersion": "analysis_quality_v9_pt",
                        "datasetVersion": "def456",
                        "provider": "local",
                    },
                },
            },
            model_name="bertimbau-base",
            model_version="analysis_v1",
            dataset_version="root123",
            provider="local",
        )
        payload = analysis_payload(analysis)
        self.assertIn("id", payload)
        self.assertIn("resumeId", payload)
        self.assertIn("status", payload)
        self.assertIn("score", payload)
        self.assertIn("completeness", payload)
        self.assertIsNone(payload["completeness"])
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
        self.assertIn("datasetVersion", payload["metadata"])
        self.assertIn("provider", payload["metadata"])
        self.assertIn("taskModels", payload["metadata"])
        self.assertIn("seniority", payload["metadata"]["taskModels"])
        self.assertEqual(payload["metadata"]["taskModels"]["quality"]["modelVersion"], "analysis_quality_v9_pt")
        self.assertIn("createdAt", payload)
        self.assertIn("updatedAt", payload)
        self.assertEqual(len(payload["insights"]["strengths"]), 1)
        self.assertIn("key", payload["insights"]["strengths"][0])
        self.assertEqual(
            payload["insights"]["strengths"][0]["key"],
            "analysis.insights.strengths.clear_structure",
        )
        self.assertEqual(len(payload["insights"]["improvements"]), 1)
        self.assertEqual(payload["insights"]["improvements"][0]["priority"], "high")

    def test_payload_drops_generic_strength_other(self):
        analysis = ResumeAnalysis.objects.create(
            user_id=self.user_a.id,
            resume_id=self.resume_a.id,
            status=AnalysisStatus.DONE,
            score=50,
            task_scores={},
            resume_content_synced_at=self._resume_content_synced_at(self.resume_a),
            payload_json={
                "insights": {
                    "strengths": [{"key": "analysis.insights.strengths.other", "params": {}}],
                    "improvements": [],
                },
            },
        )
        payload = analysis_payload(analysis)
        self.assertEqual(payload["insights"]["strengths"], [])

    def test_failed_analysis_includes_error_message(self):
        analysis = ResumeAnalysis.objects.create(
            user_id=self.user_a.id,
            resume_id=self.resume_a.id,
            status=AnalysisStatus.FAILED,
            error_message="Mock error",
            resume_content_synced_at=self._resume_content_synced_at(self.resume_a),
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


class TestRunReturns503WhenUnavailable(AnalysisAPITestCase):
    """When Celery unavailable and fallback disabled (prod), return 503."""

    @override_settings(
        CELERY_BROKER_URL="",
        CELERY_TASKS_ENABLED=True,
        ALLOW_INPROCESS_JOB_FALLBACK=False,
    )
    def test_run_returns_503_when_analysis_unavailable(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.post(
            self.run_url,
            {"resume_id": str(self.resume_a.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = resp.json() or {}
        self.assertIn("error", data)
