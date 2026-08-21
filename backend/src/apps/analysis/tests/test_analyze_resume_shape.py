"""
O formato estavel que ``analyze_resume`` devolve, e quem responde cada pilar no payload.

Separado de ``test_inference.py``, que fica com secoes, truncamento, insights e os loaders.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings

from apps.analysis.application.inference.config import get_config
from apps.analysis.application.inference.loader import clear_cache, get_quality_bundle
from apps.analysis.application.inference.resume_mapper import resume_to_text
from apps.analysis.application.inference.safety import truncate_text
from apps.analysis.application.inference.completeness import assess_completeness
from apps.analysis.application.inference.postprocess.insights import derive_insights
from apps.analysis.application.inference.resume_signals import (
    education_aligned_with_target,
    has_internship_position,
    is_thin_student_or_intern_profile,
    max_years_mentioned_in_work_context,
    structured_seniority_floor_lift,
)
from apps.analysis.application.inference import orchestrator as orchestrator_mod
from apps.analysis.application.inference.orchestrator import analyze_resume
from apps.analysis.application.inference.tasks.seniority.constants import SENIORITY_POLICY_VERSION
from apps.analysis.application.inference.tasks.quality.predict import predict_quality
from apps.analysis.application.inference.tasks.matching.predict import predict_matching

@override_settings(ANALYSIS_REQUIRE_MODEL_ANSWER=False)
class AnalyzeResumeStableShapeTest(TestCase):
    """Test analyze_resume returns stable shape."""

    def test_analyze_resume_returns_stable_shape(self) -> None:
        resume_data = {
            "data": {
                "summary": "Desenvolvedor com 3 anos.",
                "contact": {},
                "experiences": [{"company": "X", "position": "Dev", "description": ["Trabalhei em X."]}],
                "educations": [],
                "skills": [{"name": "Python"}],
                "languages": [],
            }
        }
        result = analyze_resume(resume_data, job_description_text=None, language="pt-BR")
        self.assertIn("score", result)
        self.assertIn("task_scores", result)
        self.assertIn("payload_json", result)
        self.assertIn("model_name", result)
        self.assertIn("model_version", result)
        self.assertIn("provider", result)
        self.assertIn("dataset_version", result)
        self.assertIn("seniority_rule_label", result)
        self.assertIn("seniority_final_label", result)
        self.assertIn("seniority_label_source", result)
        self.assertIn("seniority_policy_version", result)
        self.assertIn("seniority_evidence_json", result)
        self.assertIsInstance(result["score"], int)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        ts = result["task_scores"]
        self.assertIn("ats", ts)
        self.assertIn("clarity", ts)
        self.assertIn("seniority", ts)
        payload = result["payload_json"]
        self.assertIn("insights", payload)
        self.assertIn("strengths", payload["insights"])
        self.assertIn("improvements", payload["insights"])
        self.assertIn("was_truncated", payload)
        self.assertIn("completeness", payload)
        self.assertIn("score", payload["completeness"])
        self.assertIn("level", payload["completeness"])
        self.assertIn("model_metadata_by_task", payload)
        self.assertIn("seniority", payload["model_metadata_by_task"])
        self.assertIn("quality", payload["model_metadata_by_task"])

    TARGET_FIT_RESUME = {
        "data": {
            "targetPosition": "Analista",
            "summary": "Profissional com experiência.",
            "contact": {},
            "experiences": [
                {"company": "Co", "position": "Analista", "description": ["Relatórios e conciliação."]}
            ],
            "educations": [],
            "skills": [{"name": "Excel"}],
            "languages": [],
        }
    }

    def _assert_target_fit_shape(self, payload: dict, task_scores: dict, provider: str) -> None:
        self.assertIn("targetFitScore", payload)
        self.assertIn("targetFitModelVersion", payload)
        self.assertEqual(payload.get("targetFitProvider"), provider)
        meta = payload.get("model_metadata_by_task") or {}
        self.assertIn("target_fit", meta)
        self.assertEqual((meta.get("target_fit") or {}).get("provider"), provider)
        self.assertIsNotNone(task_scores.get("target_fit"))

    @override_settings(ANALYSIS_EMBEDDINGS_ENABLED=True)
    def test_target_position_is_answered_by_the_encoder(self) -> None:
        """
        With the encoder available target_fit is neural, and the payload has to say so.

        This assertion used to name `target_fit_policy`, which was correct before section 6 moved
        domain and fit onto the multilingual encoder. Left alone it froze the heuristic as the
        expected answer for the pillar, which is the opposite of what the provider table is for.
        """
        result = analyze_resume(self.TARGET_FIT_RESUME, None, "pt-BR")
        self._assert_target_fit_shape(
            result["payload_json"], result["task_scores"], "target_fit_embedding_v1"
        )

    @override_settings(ANALYSIS_EMBEDDINGS_ENABLED=False)
    def test_target_fit_falls_back_to_policy_without_the_encoder(self) -> None:
        """The policy path still has to produce the same payload shape — fallback stays tested."""
        result = analyze_resume(self.TARGET_FIT_RESUME, None, "pt-BR")
        self._assert_target_fit_shape(
            result["payload_json"], result["task_scores"], "target_fit_policy"
        )

    @override_settings(
        ANALYSIS_MODEL_VERSION_BY_TASK=(
            "quality=analysis_quality_v9_pt;"
            "matching=analysis_matching_v3_reg_pt"
        ),
        ANALYSIS_MODEL_VERSION_BY_TASK_LANG=(
            "quality:pt-BR=analysis_quality_v9_pt;"
            "quality:en-US=analysis_quality_multi_v1_light;"
            "quality:es-ES=analysis_quality_multi_v1_light;"
            "matching:pt-BR=analysis_matching_v3_reg_pt;"
            "matching:en-US=analysis_matching_multi_v1_light;"
            "matching:es-ES=analysis_matching_multi_v1_light"
        ),
        ANALYSIS_MODEL_VERSION_BY_LANG=(
            "pt-BR=analysis_v1_pt;"
            "en-US=analysis_seniority_multi_v2_light;"
            "es-ES=analysis_seniority_multi_v2_light"
        ),
        # Pinned off: matching now reports the step that answered, so with embeddings enabled the
        # version below would be matching_embeddings_v1 and the assertion would depend on .env.
        ANALYSIS_EMBEDDINGS_ENABLED=False,
    )
    def test_analyze_resume_exposes_task_specific_model_metadata(self) -> None:
        resume_data = {
            "data": {
                "summary": "Engenheiro backend com 5 anos. Implementei 10 APIs e reduzi latencia em 15%.",
                "contact": {"github": "github.com/foo"},
                "experiences": [{"company": "X", "position": "Dev", "description": ["Python e Django."]}],
                "educations": [],
                "skills": [{"name": "Python"}, {"name": "Django"}],
                "languages": [],
            }
        }
        result = analyze_resume(
            resume_data,
            job_description_text="Vaga backend com Python, Django e PostgreSQL.",
            language="pt-BR",
        )
        metadata_by_task = result["payload_json"]["model_metadata_by_task"]
        self.assertIn(
            metadata_by_task["seniority"]["modelVersion"],
            ("analysis_v1_pt", SENIORITY_POLICY_VERSION),
        )
        self.assertIn(metadata_by_task["seniority"]["provider"], ("rule_policy", "text_seniority_probe"))
        self.assertEqual(metadata_by_task["quality"]["modelVersion"], "analysis_quality_v9_pt")
        self.assertEqual(metadata_by_task["matching"]["modelVersion"], "analysis_matching_v3_reg_pt")
        self.assertIn(metadata_by_task["quality"]["provider"], ("local", "heuristics"))
