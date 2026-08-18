"""
Unit tests for analysis inference module.
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


class ResumeToTextSectionsTest(TestCase):
    """Test resume_to_text produces sections for pt/en/es."""

    def _minimal_resume_data(self) -> dict:
        return {
            "data": {
                "summary": "Profissional com 5 anos em desenvolvimento.",
                "contact": {"linkedin": "linkedin.com/in/foo", "github": "github.com/foo"},
                "experiences": [
                    {
                        "company": "Empresa X",
                        "position": "Desenvolvedor",
                        "startDate": "2020-01",
                        "endDate": "2024-12",
                        "description": ["Desenvolvi sistemas.", "Coordenei equipe."],
                    }
                ],
                "educations": [{"institution": "UFX", "course": "Computação", "degree": "Bacharelado"}],
                "skills": [{"name": "Python"}, {"name": "Django"}],
                "languages": [{"name": "Português", "level": "native"}],
            }
        }

    def test_resume_to_text_sections_pt(self) -> None:
        sections = resume_to_text(self._minimal_resume_data(), language="pt-BR")
        self.assertIn("Resumo", sections.full_text)
        self.assertIn("Experiência Profissional", sections.full_text)
        self.assertIn("Formação", sections.full_text)
        self.assertIn("Habilidades", sections.full_text)
        self.assertTrue(sections.summary)
        self.assertTrue(sections.experience)
        self.assertIn("Python", sections.skills)

    def test_resume_to_text_sections_en(self) -> None:
        sections = resume_to_text(self._minimal_resume_data(), language="en-US")
        self.assertIn("Summary", sections.full_text)
        self.assertIn("Work Experience", sections.full_text)
        self.assertIn("Education", sections.full_text)
        self.assertIn("Skills", sections.full_text)

    def test_resume_to_text_sections_es(self) -> None:
        sections = resume_to_text(self._minimal_resume_data(), language="es-ES")
        self.assertIn("Resumen", sections.full_text)
        self.assertIn("Experiencia Profesional", sections.full_text)
        self.assertIn("Formación", sections.full_text)
        self.assertIn("Habilidades", sections.full_text)


class TruncationLimitsTest(TestCase):
    """Test truncation and limits."""

    def test_truncate_no_truncation(self) -> None:
        text, truncated = truncate_text("short", 100)
        self.assertEqual(text, "short")
        self.assertFalse(truncated)

    def test_truncate_was_truncated(self) -> None:
        text = "a" * 200
        out, truncated = truncate_text(text, 50)
        self.assertEqual(len(out), 50)
        self.assertTrue(truncated)

    def test_truncate_empty(self) -> None:
        out, truncated = truncate_text("", 100)
        self.assertEqual(out, "")
        self.assertFalse(truncated)


class InsightsKeysCanonicalTest(TestCase):
    """Test insight keys are canonical for i18n."""

    def test_insights_keys_are_canonical(self) -> None:
        insights = derive_insights(
            seniority="mid",
            quality_flags={"has_metrics": False, "has_links": True, "has_action_verbs": True},
            sections=None,
            resume_text="",
        )
        for s in insights["strengths"]:
            self.assertIn("key", s)
            self.assertTrue(s["key"].startswith("analysis.insights."))
            self.assertIn("params", s)
        for i in insights["improvements"]:
            self.assertIn("key", i)
            self.assertTrue(i["key"].startswith("analysis.insights."))
            self.assertIn("params", i)
            self.assertIn(i.get("priority", "medium"), ("high", "medium", "low"))

    def test_insights_sparse_no_placeholder_strength(self) -> None:
        insights = derive_insights(
            seniority="intern",
            quality_flags={"has_metrics": False, "has_links": False, "has_action_verbs": False},
            sections=None,
            resume_text="",
            completeness_level="insufficient",
        )
        self.assertEqual(insights["strengths"], [])
        keys = [i["key"] for i in insights["improvements"]]
        self.assertIn("analysis.insights.improvements.fill_core_sections", keys)


# Exercises the fallback path on purpose: these assertions are about completeness caps, thin-
# profile guards, insights, target_fit and persistence — not about the quality model. Production
# refuses a heuristic quality score (ANALYSIS_REQUIRE_MODEL_ANSWER defaults on), so the flag is
# turned off here rather than left to a suite-wide default that would hide the policy.


# Exercises the fallback path on purpose: these assertions are about completeness caps, thin-
# profile guards, insights, target_fit and persistence — not about the quality model. Production
# refuses a heuristic quality score (ANALYSIS_REQUIRE_MODEL_ANSWER defaults on), so the flag is
# turned off here rather than left to a suite-wide default that would hide the policy.


class InferenceConfigTaskVersionSelectionTest(TestCase):
    """Language/task model mappings should select the official candidates."""

    @override_settings(
        ANALYSIS_MODEL_ROOT="../ml/models",
        ANALYSIS_MODEL_VERSION="analysis_v1_pt",
        ANALYSIS_MODEL_VERSION_BY_LANG=(
            "pt-BR=analysis_v1_pt;"
            "en-US=analysis_seniority_multi_v2_light;"
            "es-ES=analysis_seniority_multi_v2_light"
        ),
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
    )
    def test_language_and_task_specific_versions_are_parsed(self) -> None:
        config = get_config(settings)
        self.assertEqual(config["model_version"], "analysis_v1_pt")
        self.assertEqual(config["model_version_by_lang"]["pt-BR"], "analysis_v1_pt")
        self.assertEqual(config["model_version_by_lang"]["en-US"], "analysis_seniority_multi_v2_light")
        self.assertEqual(config["model_version_by_lang"]["es-ES"], "analysis_seniority_multi_v2_light")
        self.assertEqual(config["model_version_by_task"]["quality"], "analysis_quality_v9_pt")
        self.assertEqual(config["model_version_by_task"]["matching"], "analysis_matching_v3_reg_pt")
        self.assertEqual(config["model_version_by_task_lang"]["quality:pt-BR"], "analysis_quality_v9_pt")
        self.assertEqual(config["model_version_by_task_lang"]["quality:en-US"], "analysis_quality_multi_v1_light")
        self.assertEqual(config["model_version_by_task_lang"]["quality:es-ES"], "analysis_quality_multi_v1_light")
        self.assertEqual(config["model_version_by_task_lang"]["matching:pt-BR"], "analysis_matching_v3_reg_pt")
        self.assertEqual(config["model_version_by_task_lang"]["matching:en-US"], "analysis_matching_multi_v1_light")
        self.assertEqual(config["model_version_by_task_lang"]["matching:es-ES"], "analysis_matching_multi_v1_light")


class QualityBundleTaskMismatchTest(TestCase):
    """Quality loader should not try to load a seniority-only artifact."""

    def tearDown(self) -> None:
        clear_cache()

    @patch("apps.analysis.application.inference.loader._resolve_model_path")
    def test_quality_bundle_skips_model_when_metadata_task_mismatch(
        self,
        resolve_model_path,
    ) -> None:
        resolve_model_path.return_value = (
            "c:/fake-model/hf",
            "analysis_v1_pt",
            {"task": "seniority", "model_version": "analysis_v1_pt"},
        )

        model, extra = get_quality_bundle(
            language="pt-BR",
            config={"model_mode": "hf", "allow_heuristics_fallback": True},
        )

        self.assertIsNone(model)
        self.assertEqual(extra["provider"], "heuristics-only")


class MatchingPredictorCustomModelTest(TestCase):
    """Matching predictor should support the trained bi-encoder artifact."""

    def test_predict_matching_uses_custom_bundle(self) -> None:
        class DummyTokenizer:
            def __call__(self, *args, **kwargs):
                return {
                    "input_ids": [[1, 2, 3]],
                    "attention_mask": [[1, 1, 1]],
                }

        class DummyScore:
            def __init__(self, value: float):
                self._value = value

            def squeeze(self, *_args, **_kwargs):
                return self

            def item(self) -> float:
                return self._value

        class DummyModel:
            def __call__(self, **kwargs):
                return DummyScore(0.83)

        score, top = predict_matching(
            resume_text="Python Django PostgreSQL Docker APIs",
            job_text="Buscamos backend com Python Django APIs e PostgreSQL",
            language="pt-BR",
            matching_bundle=(
                DummyModel(),
                {
                    "tokenizer": DummyTokenizer(),
                    "kind": "matching-biencoder",
                    "metadata": {"input_limits": {"max_tokens": 128}},
                },
            ),
        )

        self.assertEqual(score, 83)
        self.assertTrue(len(top) > 0)
