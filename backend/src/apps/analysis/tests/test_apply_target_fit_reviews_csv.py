"""apply_target_fit_reviews_from_csv management command."""
from __future__ import annotations

import csv
import tempfile
import uuid
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.infrastructure.models import User, UserStatus
from apps.analysis.application.internal_review import pseudo_key, resolve_review_hash_salt
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume, ResumeStatus


class ApplyTargetFitReviewsCsvTest(TestCase):
    def test_writes_gold_score_and_source(self) -> None:
        email = f"tf-csv-{uuid.uuid4().hex[:10]}@local.seed.invalid"
        user = User.objects.create(email=email, full_name="TF CSV", status=UserStatus.ACTIVE)
        resume = Resume.objects.create(
            user=user,
            name="CV",
            status=ResumeStatus.DRAFT,
            target_position="Analista",
        )
        analysis = ResumeAnalysis.objects.create(
            user=user,
            resume=resume,
            status=AnalysisStatus.DONE,
            score=70,
            payload_json={"completeness": {"score": 60, "level": "adequate"}},
        )
        salt = resolve_review_hash_salt()
        key = pseudo_key(raw_id=str(analysis.id), salt=salt)

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.csv"
            with p.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(
                    f,
                    fieldnames=["analysis_key", "review_fit_score", "review_note"],
                    delimiter=";",
                )
                w.writeheader()
                w.writerow({"analysis_key": key, "review_fit_score": "58", "review_note": "ajuste fronteira"})

            call_command("apply_target_fit_reviews_from_csv", csv=str(p))

        analysis.refresh_from_db()
        pj = analysis.payload_json or {}
        self.assertEqual(pj.get("targetFitGoldScore"), 58)
        self.assertEqual(pj.get("targetFitLabelSource"), "review")
        self.assertIn("ajuste", str(pj.get("targetFitReviewNote") or ""))

    def test_review_seniority_label_only(self) -> None:
        email = f"tf-sen-{uuid.uuid4().hex[:10]}@local.seed.invalid"
        user = User.objects.create(email=email, full_name="TF Sen", status=UserStatus.ACTIVE)
        resume = Resume.objects.create(
            user=user,
            name="CV2",
            status=ResumeStatus.DRAFT,
            target_position="Dev",
        )
        analysis = ResumeAnalysis.objects.create(
            user=user,
            resume=resume,
            status=AnalysisStatus.DONE,
            score=60,
            payload_json={},
        )
        salt = resolve_review_hash_salt()
        key = pseudo_key(raw_id=str(analysis.id), salt=salt)

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r2.csv"
            with p.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(
                    f,
                    fieldnames=["analysis_key", "review_seniority_label"],
                    delimiter=";",
                )
                w.writeheader()
                w.writerow({"analysis_key": key, "review_seniority_label": "senior"})

            call_command("apply_target_fit_reviews_from_csv", csv=str(p))

        analysis.refresh_from_db()
        self.assertEqual((analysis.seniority_review_label or "").strip(), "senior")
