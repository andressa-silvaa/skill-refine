"""Internal low-confidence review API (token-gated, no JWT, pseudo-keys only)."""
from __future__ import annotations

import json

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.infrastructure.models import User
from apps.analysis.application.internal_review import pseudo_key, resolve_review_hash_salt
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume, ResumeStatus


class TestLowConfidenceInternalReview(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/analysis/internal/low-confidence"
        self.export_url = "/analysis/internal/low-confidence/export"
        self.metrics_url = "/analysis/internal/metrics/seniority"
        self.review_url = "/analysis/internal/review/seniority"
        self.user, _ = User.objects.get_or_create(
            email="internal-review@test.local",
            defaults={"full_name": "Internal Review", "status": "active"},
        )
        self.resume = Resume.objects.create(
            user_id=self.user.id,
            name="R",
            status=ResumeStatus.DRAFT,
            target_position="Dev",
        )
        self.resume.refresh_from_db()

    @override_settings(ANALYSIS_INTERNAL_REVIEW_SECRET="")
    def test_secret_unset_returns_403(self):
        resp = self.client.get(self.url, HTTP_X_ANALYSIS_INTERNAL_TOKEN="anything")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(ANALYSIS_INTERNAL_REVIEW_SECRET="test-secret", DEBUG=True)
    def test_wrong_token_returns_403(self):
        resp = self.client.get(self.url, HTTP_X_ANALYSIS_INTERNAL_TOKEN="wrong")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(ANALYSIS_INTERNAL_REVIEW_SECRET="test-secret", DEBUG=True)
    def test_debug_false_weak_secret_returns_403_even_with_valid_token(self):
        with override_settings(ANALYSIS_INTERNAL_REVIEW_SECRET="short-secret", DEBUG=False):
            resp = self.client.get(
                self.url,
                HTTP_X_ANALYSIS_INTERNAL_TOKEN="short-secret",
            )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(
        ANALYSIS_INTERNAL_REVIEW_SECRET="this-is-a-long-production-secret",
        DEBUG=False,
        ANALYSIS_INTERNAL_SECRET_MIN_LENGTH=20,
    )
    def test_debug_false_strong_secret_allows_access(self):
        ResumeAnalysis.objects.create(
            user_id=self.user.id,
            resume_id=self.resume.id,
            status=AnalysisStatus.DONE,
            score=40,
            resume_content_synced_at=self.resume.updated_at,
            payload_json={
                "seniorityClass": "junior",
                "seniorityConfidence": "low",
                "seniorityRuleBase": "junior",
                "seniorityMlStatus": "skipped_gating",
                "insufficientData": True,
                "gatingReasons": ["no_experiences"],
                "completeness": {"score": 20, "level": "insufficient"},
            },
        )
        resp = self.client.get(
            self.url,
            {"confidence": "low"},
            HTTP_X_ANALYSIS_INTERNAL_TOKEN="this-is-a-long-production-secret",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    @override_settings(ANALYSIS_INTERNAL_REVIEW_SECRET="test-secret", DEBUG=True)
    def test_valid_token_returns_pseudo_keys_not_raw_ids(self):
        salt = resolve_review_hash_salt()
        analysis = ResumeAnalysis.objects.create(
            user_id=self.user.id,
            resume_id=self.resume.id,
            status=AnalysisStatus.DONE,
            score=40,
            resume_content_synced_at=self.resume.updated_at,
            payload_json={
                "seniorityClass": "junior",
                "seniorityConfidence": "low",
                "seniorityRuleBase": "junior",
                "seniorityMlStatus": "skipped_gating",
                "insufficientData": True,
                "gatingReasons": ["no_experiences"],
                "completeness": {"score": 20, "level": "insufficient"},
            },
        )
        ResumeAnalysis.objects.create(
            user_id=self.user.id,
            resume_id=self.resume.id,
            status=AnalysisStatus.DONE,
            score=80,
            resume_content_synced_at=self.resume.updated_at,
            payload_json={
                "seniorityClass": "mid",
                "seniorityConfidence": "high",
                "seniorityRuleBase": "mid",
            },
        )
        resp = self.client.get(
            self.url,
            {"confidence": "low", "limit": "10"},
            HTTP_X_ANALYSIS_INTERNAL_TOKEN="test-secret",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body["confidence"], "low")
        self.assertEqual(body["count"], 1)
        item = body["items"][0]
        self.assertEqual(item["seniorityLabel"], "junior")
        self.assertEqual(item["seniorityConfidence"], "low")
        self.assertTrue(item["insufficientData"])
        self.assertEqual(item["completenessScore"], 20)
        self.assertNotIn("userId", item)
        self.assertNotIn("resumeId", item)
        self.assertNotIn("analysisId", item)
        self.assertEqual(item["analysisKey"], pseudo_key(raw_id=str(analysis.id), salt=salt))
        self.assertEqual(item["resumeKey"], pseudo_key(raw_id=str(self.resume.id), salt=salt))

    @override_settings(ANALYSIS_INTERNAL_REVIEW_SECRET="test-secret", DEBUG=True)
    def test_has_reason_filters(self):
        ResumeAnalysis.objects.create(
            user_id=self.user.id,
            resume_id=self.resume.id,
            status=AnalysisStatus.DONE,
            score=30,
            resume_content_synced_at=self.resume.updated_at,
            payload_json={
                "seniorityClass": "junior",
                "seniorityConfidence": "low",
                "seniorityRuleBase": "junior",
                "gatingReasons": ["no_experiences"],
                "completeness": {"score": 5, "level": "insufficient"},
            },
        )
        ResumeAnalysis.objects.create(
            user_id=self.user.id,
            resume_id=self.resume.id,
            status=AnalysisStatus.DONE,
            score=50,
            resume_content_synced_at=self.resume.updated_at,
            payload_json={
                "seniorityClass": "junior",
                "seniorityConfidence": "low",
                "seniorityRuleBase": "junior",
                "gatingReasons": ["completeness_insufficient"],
                "completeness": {"score": 10, "level": "insufficient"},
            },
        )
        resp = self.client.get(
            self.url,
            {"confidence": "low", "has_reason": "no_experiences"},
            HTTP_X_ANALYSIS_INTERNAL_TOKEN="test-secret",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["count"], 1)

    @override_settings(ANALYSIS_INTERNAL_REVIEW_SECRET="test-secret", DEBUG=True)
    def test_export_returns_jsonl_rows(self):
        ResumeAnalysis.objects.create(
            user_id=self.user.id,
            resume_id=self.resume.id,
            status=AnalysisStatus.DONE,
            score=40,
            resume_content_synced_at=self.resume.updated_at,
            payload_json={
                "seniorityClass": "junior",
                "seniorityConfidence": "low",
                "seniorityRuleBase": "junior",
                "gatingReasons": [],
                "completeness": {"score": 30, "level": "partial"},
            },
        )
        resp = self.client.get(
            self.export_url,
            {"confidence": "low", "limit": "5"},
            HTTP_X_ANALYSIS_INTERNAL_TOKEN="test-secret",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        raw = b"".join(resp.streaming_content)
        line = raw.decode("utf-8").strip().split("\n")[0]
        row = json.loads(line)
        self.assertEqual(row.get("schema_version"), "1.1")
        self.assertIn("signals", row)
        self.assertNotIn("text_sanitized", row)

    @override_settings(ANALYSIS_INTERNAL_REVIEW_SECRET="test-secret", DEBUG=True)
    def test_metrics_endpoint_returns_aggregates(self):
        ResumeAnalysis.objects.create(
            user_id=self.user.id,
            resume_id=self.resume.id,
            status=AnalysisStatus.DONE,
            score=40,
            resume_content_synced_at=self.resume.updated_at,
            payload_json={
                "seniorityClass": "junior",
                "seniorityConfidence": "low",
                "gatingReasons": ["no_experiences"],
            },
        )
        resp = self.client.get(
            self.metrics_url,
            {"days": "30"},
            HTTP_X_ANALYSIS_INTERNAL_TOKEN="test-secret",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("bySeniorityConfidence", data)
        self.assertIn("topGatingReasons", data)

    @override_settings(ANALYSIS_INTERNAL_REVIEW_SECRET="test-secret", DEBUG=True)
    def test_post_review_seniority_sets_gold_label(self):
        analysis = ResumeAnalysis.objects.create(
            user_id=self.user.id,
            resume_id=self.resume.id,
            status=AnalysisStatus.DONE,
            score=40,
            resume_content_synced_at=self.resume.updated_at,
            seniority_rule_label="junior",
            seniority_final_label="junior",
            seniority_label_source="rule",
            seniority_policy_version="v1.0",
            seniority_confidence="low",
            payload_json={
                "seniorityClass": "junior",
                "seniorityConfidence": "low",
                "seniorityRuleBase": "junior",
                "seniorityEvidence": [],
                "gatingReasons": [],
                "completeness": {"score": 30, "level": "partial"},
            },
            task_scores={"ats": 40, "clarity": 40, "seniority": 50},
        )
        salt = resolve_review_hash_salt()
        key = pseudo_key(raw_id=str(analysis.id), salt=salt)
        resp = self.client.post(
            self.review_url,
            {"analysisKey": key, "reviewLabel": "mid", "reviewNote": "ok"},
            format="json",
            HTTP_X_ANALYSIS_INTERNAL_TOKEN="test-secret",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.json().get("ok"))
        analysis.refresh_from_db()
        self.assertEqual(analysis.seniority_review_label, "mid")
        self.assertEqual(analysis.seniority_final_label, "mid")
        self.assertEqual(analysis.seniority_label_source, "review")
        self.assertEqual(analysis.seniority_confidence, "high")
        pj = analysis.payload_json or {}
        self.assertEqual(pj.get("seniorityClass"), "mid")
