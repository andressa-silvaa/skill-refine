"""
Unit tests for analysis inference module.
"""
from __future__ import annotations

from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings

from apps.analysis.application.inference.config import get_config
from apps.analysis.application.inference.loader import clear_cache, get_quality_bundle
from apps.analysis.application.inference.resume_mapper import resume_to_text
from apps.analysis.application.inference.safety import truncate_text
from apps.analysis.application.inference.postprocess.insights import derive_insights
from apps.analysis.application.inference.orchestrator import analyze_resume
from apps.analysis.application.inference.predictors.quality import predict_quality
from apps.analysis.application.inference.predictors.matching import predict_matching


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
        self.assertIn("model_metadata_by_task", payload)
        self.assertIn("seniority", payload["model_metadata_by_task"])
        self.assertIn("quality", payload["model_metadata_by_task"])

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
        self.assertEqual(metadata_by_task["seniority"]["modelVersion"], "analysis_v1_pt")
        self.assertEqual(metadata_by_task["quality"]["modelVersion"], "analysis_quality_v9_pt")
        self.assertEqual(metadata_by_task["matching"]["modelVersion"], "analysis_matching_v3_reg_pt")
        self.assertIn(metadata_by_task["quality"]["provider"], ("local", "heuristics"))


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


class QualityPredictorOrdinalModelTest(TestCase):
    """Quality predictor should map ordinal HF logits back to 0-100 score."""

    def test_predict_quality_maps_classification_logits_to_score(self) -> None:
        class DummyTokenizer:
            def __call__(self, *args, **kwargs):
                return {
                    "input_ids": [[1, 2, 3]],
                    "attention_mask": [[1, 1, 1]],
                }

        class DummyConfig:
            id2label = {0: "poor", 1: "ok", 2: "good", 3: "excellent"}

        class DummyArgmax:
            def __init__(self, value: int):
                self._value = value

            def item(self) -> int:
                return self._value

        class DummyLogits:
            ndim = 2
            shape = (1, 4)

            def argmax(self, dim: int = -1) -> DummyArgmax:
                return DummyArgmax(2)

        class DummyModel:
            config = DummyConfig()

            def __call__(self, **kwargs):
                return type("Out", (), {"logits": DummyLogits()})()

        score, flags = predict_quality(
            resume_text="Implementou melhorias com 20% de ganho e github.com/foo",
            language="pt-BR",
            sections=None,
            quality_bundle=(
                DummyModel(),
                {
                    "tokenizer": DummyTokenizer(),
                    "metadata": {"input_limits": {"max_tokens": 128}},
                },
            ),
        )

        self.assertEqual(score, 75)
        self.assertTrue(flags["has_metrics"])


class QualityPredictorHybridModelTest(TestCase):
    """Quality predictor should support hybrid sklearn-like bundles."""

    def test_predict_quality_uses_hybrid_bundle(self) -> None:
        class DummyVectorizer:
            def transform(self, rows):
                self.rows = rows
                return rows

        class DummyEstimator:
            classes_ = [0, 1, 2, 3]

            def predict_proba(self, rows):
                return [[0.05, 0.10, 0.70, 0.15]]

        score, flags = predict_quality(
            resume_text="Implementei 12 endpoints, reduzi o tempo em 20% e publiquei github.com/foo",
            language="pt-BR",
            sections=None,
            seniority_hint="junior",
            quality_bundle=(
                {
                    "vectorizer": DummyVectorizer(),
                    "estimator": DummyEstimator(),
                    "quality_level_to_score": {"poor": 30, "ok": 55, "good": 75, "excellent": 92},
                },
                {
                    "kind": "hybrid",
                    "metadata": {"artifact_kind": "hybrid"},
                    "provider": "hybrid-local",
                },
            ),
        )

        self.assertGreaterEqual(score, 70)
        self.assertLessEqual(score, 80)
        self.assertTrue(flags["has_links"])


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
