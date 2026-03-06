from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.infrastructure.models import User
from apps.resumes.infrastructure.models import Resume, ResumeExport, ResumeExportStatus, ResumeStatus


@override_settings(PDF_EXPORTS_EAGER=True, CELERY_TASKS_ENABLED=False)
class ResumePdfExportsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_a, _ = User.objects.get_or_create(
            email="resume-pdf-a@test.local",
            defaults={"full_name": "User A", "status": "active"},
        )
        self.user_b, _ = User.objects.get_or_create(
            email="resume-pdf-b@test.local",
            defaults={"full_name": "User B", "status": "active"},
        )
        self.resume = Resume.objects.create(
            user_id=self.user_a.id,
            name="Resume PDF",
            status=ResumeStatus.COMPLETE,
            target_position="Backend Engineer",
            summary="Summary",
        )
        self.client.force_authenticate(user=self.user_a)

    @staticmethod
    def _render_result(_url: str) -> tuple[bytes, dict]:
        return b"%PDF-1.4 fake", {"render_total_ms": 111, "pdf_render_ms": 44}

    def test_pdf_export_cache_hit_is_reused(self):
        with patch(
            "apps.resumes.interfaces.api.pdf_exports.render_resume_pdf_from_preview",
            side_effect=self._render_result,
        ) as render_mock:
            first = self.client.post(f"/resumes/api/resumes/{self.resume.id}/pdf/start")
            self.assertEqual(first.status_code, status.HTTP_202_ACCEPTED)
            export_id = first.json()["exportId"]

            status_resp = self.client.get(f"/resumes/api/resumes/{self.resume.id}/pdf/status/{export_id}")
            self.assertEqual(status_resp.status_code, status.HTTP_200_OK)
            self.assertEqual(status_resp.json()["status"], "ready")
            self.assertEqual(render_mock.call_count, 1)

            second = self.client.post(f"/resumes/api/resumes/{self.resume.id}/pdf/start")
            self.assertEqual(second.status_code, status.HTTP_200_OK)
            self.assertEqual(second.json()["status"], "ready")
            self.assertTrue(second.json()["cacheHit"])
            self.assertEqual(render_mock.call_count, 1)

    def test_pdf_export_cache_invalidates_after_resume_update(self):
        with patch(
            "apps.resumes.interfaces.api.pdf_exports.render_resume_pdf_from_preview",
            side_effect=self._render_result,
        ):
            first = self.client.post(f"/resumes/api/resumes/{self.resume.id}/pdf/start")
            export_id_1 = first.json()["exportId"]
            status_1 = self.client.get(f"/resumes/api/resumes/{self.resume.id}/pdf/status/{export_id_1}")
            self.assertEqual(status_1.json()["status"], "ready")
            fingerprint_1 = status_1.json()["fingerprint"]

            self.resume.summary = "Summary updated"
            self.resume.save(update_fields=["summary", "updated_at"])

            second = self.client.post(f"/resumes/api/resumes/{self.resume.id}/pdf/start")
            export_id_2 = second.json()["exportId"]
            status_2 = self.client.get(f"/resumes/api/resumes/{self.resume.id}/pdf/status/{export_id_2}")
            self.assertEqual(status_2.json()["status"], "ready")
            fingerprint_2 = status_2.json()["fingerprint"]

            self.assertNotEqual(fingerprint_1, fingerprint_2)

    def test_pdf_export_async_flow_marks_ready(self):
        with patch(
            "apps.resumes.interfaces.api.pdf_exports.render_resume_pdf_from_preview",
            side_effect=self._render_result,
        ):
            start = self.client.post(f"/resumes/api/resumes/{self.resume.id}/pdf/start")
            self.assertEqual(start.status_code, status.HTTP_202_ACCEPTED)
            export_id = start.json()["exportId"]

            export = ResumeExport.objects.get(id=export_id)
            self.assertEqual(export.status, ResumeExportStatus.READY)
            self.assertTrue(export.storage_path)

            status_resp = self.client.get(f"/resumes/api/resumes/{self.resume.id}/pdf/status/{export_id}")
            self.assertEqual(status_resp.status_code, status.HTTP_200_OK)
            payload = status_resp.json()
            self.assertEqual(payload["status"], "ready")
            self.assertIn("downloadPath", payload)

    def test_pdf_export_respects_ownership(self):
        with patch(
            "apps.resumes.interfaces.api.pdf_exports.render_resume_pdf_from_preview",
            side_effect=self._render_result,
        ):
            start = self.client.post(f"/resumes/api/resumes/{self.resume.id}/pdf/start")
            export_id = start.json()["exportId"]

        self.client.force_authenticate(user=self.user_b)
        status_resp = self.client.get(f"/resumes/api/resumes/{self.resume.id}/pdf/status/{export_id}")
        self.assertEqual(status_resp.status_code, status.HTTP_404_NOT_FOUND)

        download_resp = self.client.get(f"/resumes/api/resumes/{self.resume.id}/pdf?export_id={export_id}")
        self.assertEqual(download_resp.status_code, status.HTTP_404_NOT_FOUND)
