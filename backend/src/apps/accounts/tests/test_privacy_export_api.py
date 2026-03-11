from __future__ import annotations

import json

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.infrastructure.models import User, UserPreferences
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.audit.models import AuditLog
from apps.resumes.infrastructure.models import Resume, ResumeStatus, ResumeVersion


class PrivacyExportApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/accounts/profile/privacy/export"
        self.user_a, _ = User.objects.get_or_create(
            email="privacy-a@test.local",
            defaults={"full_name": "User A", "status": "active"},
        )
        self.user_b, _ = User.objects.get_or_create(
            email="privacy-b@test.local",
            defaults={"full_name": "User B", "status": "active"},
        )

    def test_requires_auth(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_download_contains_only_authenticated_user_data(self):
        prefs = UserPreferences.objects.create(
            user_id=self.user_a.id,
            language="pt-BR",
            theme="dark",
            accent_color="blue",
            email_notifications_enabled=False,
        )
        resume_a = Resume.objects.create(
            user_id=self.user_a.id,
            name="Resume A",
            status=ResumeStatus.COMPLETE,
            score=83,
        )
        resume_b = Resume.objects.create(
            user_id=self.user_b.id,
            name="Resume B",
            status=ResumeStatus.COMPLETE,
            score=99,
        )
        ResumeVersion.objects.create(
            resume_id=resume_a.id,
            user_id=self.user_a.id,
            version_number=1,
            is_current=True,
            snapshot_json={"name": "Resume A"},
            change_summary_json=["first version"],
            score=83,
        )
        ResumeVersion.objects.create(
            resume_id=resume_b.id,
            user_id=self.user_b.id,
            version_number=1,
            is_current=True,
            snapshot_json={"name": "Resume B"},
            change_summary_json=["first version"],
            score=99,
        )
        ResumeAnalysis.objects.create(
            user_id=self.user_a.id,
            resume_id=resume_a.id,
            status=AnalysisStatus.DONE,
            score=88,
            task_scores={"ats": 88, "clarity": 84, "seniority": 76, "matching": 80},
            payload_json={"insights": {"strengths": [], "improvements": []}},
            model_name="model-a",
            model_version="v1",
            provider="local",
        )
        ResumeAnalysis.objects.create(
            user_id=self.user_b.id,
            resume_id=resume_b.id,
            status=AnalysisStatus.DONE,
            score=95,
            task_scores={"ats": 95, "clarity": 95, "seniority": 95},
            payload_json={"insights": {"strengths": [], "improvements": []}},
        )
        AuditLog.objects.create(
            action="accounts.preference.updated",
            actor_user_id=self.user_a.id,
            subject_user_id=self.user_a.id,
            metadata={"k": "v"},
        )
        AuditLog.objects.create(
            action="accounts.preference.updated",
            actor_user_id=self.user_b.id,
            subject_user_id=self.user_b.id,
            metadata={"k": "v"},
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response["Content-Type"].startswith("application/json"))
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        self.assertIn("skill-refine-data-export-", response["Content-Disposition"])

        data = json.loads(response.content.decode("utf-8"))
        self.assertIn("meta", data)
        self.assertEqual(data["account"]["id"], str(self.user_a.id))
        self.assertEqual(data["preferences"]["theme"], prefs.theme)

        resume_ids = {item["id"] for item in data["resumes"]}
        self.assertIn(str(resume_a.id), resume_ids)
        self.assertNotIn(str(resume_b.id), resume_ids)

        version_resume_ids = {item["resumeId"] for item in data["versionHistory"]}
        self.assertIn(str(resume_a.id), version_resume_ids)
        self.assertNotIn(str(resume_b.id), version_resume_ids)

        analysis_resume_ids = {item["resumeId"] for item in data["analyses"]}
        self.assertIn(str(resume_a.id), analysis_resume_ids)
        self.assertNotIn(str(resume_b.id), analysis_resume_ids)

        audit_actor_ids = {item["actorUserId"] for item in data["auditLogs"] if item["actorUserId"]}
        self.assertIn(str(self.user_a.id), audit_actor_ids)
        self.assertNotIn(str(self.user_b.id), audit_actor_ids)

        serialized = json.dumps(data)
        self.assertNotIn("password_hash", serialized)
        self.assertNotIn("refresh_token_hash", serialized)
        self.assertNotIn("token_hash", serialized)

    def test_user_without_resumes_can_export_account_data(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["account"]["id"], str(self.user_a.id))
        self.assertEqual(data["resumes"], [])
        self.assertEqual(data["versionHistory"], [])
        self.assertEqual(data["analyses"], [])

