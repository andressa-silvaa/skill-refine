"""Dataset export helpers (sanitization + empty iterator)."""
from __future__ import annotations

from django.test import TestCase

from apps.accounts.infrastructure.models import User
from apps.analysis.application.dataset_export import (
    build_seniority_dataset_record,
    iter_seniority_export_rows,
    sanitize_resume_text,
)
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume, ResumeStatus


class TestSanitizeResumeText(TestCase):
    def test_redacts_email_and_truncates(self):
        raw = "a@b.com " + ("word " * 3000)
        out = sanitize_resume_text(raw, max_chars=200)
        self.assertIn("[redacted-email]", out)
        self.assertLessEqual(len(out), 200)


class TestIterSeniorityExportRows(TestCase):
    def test_yields_nothing_when_no_analyses(self):
        self.assertEqual(list(iter_seniority_export_rows(limit=5)), [])


class TestBuildSeniorityDatasetRecord(TestCase):
    def test_schema_v1_fields(self):
        user, _ = User.objects.get_or_create(
            email="dataset-export@test.local",
            defaults={"full_name": "D", "status": "active"},
        )
        resume = Resume.objects.create(
            user_id=user.id,
            name="CV",
            status=ResumeStatus.DRAFT,
            target_position="Dev",
        )
        resume.refresh_from_db()
        analysis = ResumeAnalysis.objects.create(
            user_id=user.id,
            resume_id=resume.id,
            status=AnalysisStatus.DONE,
            score=55,
            task_scores={"ats": 55, "clarity": 55, "seniority": 50},
            resume_content_synced_at=resume.updated_at,
            payload_json={
                "seniorityClass": "junior",
                "seniorityRuleBase": "junior",
                "seniorityConfidence": "medium",
                "seniorityMlStatus": "noop",
                "insufficientData": False,
                "gatingReasons": [],
                "completeness": {"score": 40, "level": "partial"},
            },
            model_version="mv1",
            provider="local",
        )
        analysis = (
            ResumeAnalysis.objects.filter(pk=analysis.pk)
            .select_related("resume", "user")
            .prefetch_related(
                "resume__resumecontact",
                "resume__resumeexperience_set__resumeexperiencebullet_set",
                "resume__resumeeducation_set",
                "resume__resumeskill_set",
                "resume__resumelanguage_set",
            )
            .get()
        )
        row = build_seniority_dataset_record(
            analysis, hash_salt="testsalt", include_text=False, schema_version="1.0"
        )
        self.assertEqual(row["schema_version"], "1.0")
        self.assertEqual(row["dataset_kind"], "seniority")
        self.assertIn("analysis_key", row)
        self.assertIn("resume_key", row)
        self.assertIn("user_key", row)
        self.assertEqual(row["labels"]["seniority_label"], "junior")
        self.assertEqual(row["targets"]["overall_score"], 55)
        self.assertIn("signals", row)
        self.assertNotIn("text_sanitized", row)

        row_full = build_seniority_dataset_record(
            analysis, hash_salt="testsalt", include_text=True, schema_version="1.0"
        )
        self.assertIn("text_sanitized", row_full)

    def test_schema_v1_1_uses_persisted_final_label(self):
        user, _ = User.objects.get_or_create(
            email="dataset-export-v11@test.local",
            defaults={"full_name": "D", "status": "active"},
        )
        resume = Resume.objects.create(
            user_id=user.id,
            name="CV",
            status=ResumeStatus.DRAFT,
            target_position="Dev",
        )
        resume.refresh_from_db()
        analysis = ResumeAnalysis.objects.create(
            user_id=user.id,
            resume_id=resume.id,
            status=AnalysisStatus.DONE,
            score=60,
            task_scores={"ats": 60, "clarity": 60, "seniority": 75},
            resume_content_synced_at=resume.updated_at,
            seniority_rule_label="junior",
            seniority_final_label="mid",
            seniority_label_source="review",
            seniority_policy_version="v1.0",
            seniority_confidence="high",
            payload_json={
                "seniorityClass": "junior",
                "seniorityRuleBase": "junior",
                "seniorityConfidence": "low",
                "seniorityMlStatus": "noop",
                "insufficientData": False,
                "gatingReasons": [],
                "completeness": {"score": 60, "level": "adequate"},
            },
            model_version="mv1",
            provider="local",
        )
        analysis = (
            ResumeAnalysis.objects.filter(pk=analysis.pk)
            .select_related("resume", "user")
            .prefetch_related(
                "resume__resumecontact",
                "resume__resumeexperience_set__resumeexperiencebullet_set",
                "resume__resumeeducation_set",
                "resume__resumeskill_set",
                "resume__resumelanguage_set",
            )
            .get()
        )
        row = build_seniority_dataset_record(analysis, hash_salt="testsalt", include_text=False)
        self.assertEqual(row["schema_version"], "1.1")
        self.assertEqual(row["labels"]["seniority_label"], "mid")
        self.assertEqual(row["labels"]["rule_label"], "junior")
        self.assertEqual(row["labels"]["source"], "review")
        self.assertTrue(row["labels"]["reviewed"])
        self.assertEqual(row["labels"]["confidence"], "high")
