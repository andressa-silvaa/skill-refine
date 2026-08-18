"""
O contrato do payload que a API devolve: campos obrigatorios e formato estavel.

Separado de ``test_analysis_api.py``, que cobre autenticacao, propriedade e o ciclo de execucao.
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

from .test_analysis_api import AnalysisAPITestCase


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
