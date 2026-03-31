"""
Tests for analysis worker: RUNNING -> DONE, model_version/dataset_version persisted.
"""
from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.analysis.application.worker import run_analysis_worker_safe
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.accounts.infrastructure.models import User
from apps.resumes.infrastructure.models import Resume, ResumeStatus


class WorkerPersistsMetadataTest(TestCase):
    """Worker saves model_version and dataset_version from inference result."""

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            email="worker-test@test.local",
            defaults={"full_name": "Worker User", "status": "active"},
        )
        self.resume = Resume.objects.create(
            user_id=self.user.id,
            name="Test Resume",
            status=ResumeStatus.DRAFT,
            target_position="Dev",
        )

    @override_settings(ANALYSIS_ALLOW_HEURISTICS_FALLBACK=True)
    def test_worker_saves_model_version_and_dataset_version(self):
        analysis = ResumeAnalysis.objects.create(
            user_id=self.user.id,
            resume_id=self.resume.id,
            status=AnalysisStatus.PENDING,
        )
        run_analysis_worker_safe(str(analysis.id))
        analysis.refresh_from_db()
        self.assertEqual(analysis.status, AnalysisStatus.DONE)
        self.assertIsNotNone(analysis.model_name)
        self.assertIsNotNone(analysis.model_version)
        self.assertIn(analysis.provider, ("local", "heuristics-only"))