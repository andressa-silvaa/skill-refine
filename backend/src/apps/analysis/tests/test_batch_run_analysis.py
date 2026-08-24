"""batch_run_analysis management command (small sync run)."""
from __future__ import annotations

import uuid

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.infrastructure.models import User, UserStatus
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume, ResumeStatus, ResumeTag


# Exercises the fallback path on purpose: these assertions are about completeness caps, thin-
# profile guards, insights, target_fit and persistence — not about the quality model. Production
# refuses a heuristic quality score (ANALYSIS_REQUIRE_MODEL_ANSWER defaults on), so the flag is
# turned off here rather than left to a suite-wide default that would hide the policy.
@override_settings(ANALYSIS_REQUIRE_MODEL_ANSWER=False)
class BatchRunAnalysisCommandTest(TestCase):
    def test_sync_creates_done_analyses(self):
        email = f"batch-sync-{uuid.uuid4().hex[:10]}@local.seed.invalid"
        user = User.objects.create(email=email, full_name="Batch Test", status=UserStatus.ACTIVE)
        for i in range(5):
            resume = Resume.objects.create(
                user_id=user.id,
                name=f"Batch Test Resume {i}",
                status=ResumeStatus.DRAFT,
                target_position="Desenvolvedor de Software",
                summary="Profissional de tecnologia focado em entrega e aprendizado contínuo.",
            )
            ResumeTag.objects.create(resume=resume, label="seed_synthetic", position_index=0)
        n_before = ResumeAnalysis.objects.filter(user_id=user.id).count()
        call_command(
            "batch_run_analysis",
            user_email=email,
            limit=5,
            concurrency=1,
            sync=True,
            resume_tag="seed_synthetic",
            sleep_ms=0,
        )
        n_after = ResumeAnalysis.objects.filter(user_id=user.id).count()
        self.assertGreater(n_after, n_before)
        done = ResumeAnalysis.objects.filter(user_id=user.id, status=AnalysisStatus.DONE).count()
        self.assertGreaterEqual(done, 1)
