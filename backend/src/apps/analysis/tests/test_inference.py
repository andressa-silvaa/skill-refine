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


class CompletenessAssessmentTest(TestCase):
    """Completeness gates neural models and caps."""

    def test_empty_resume_is_insufficient(self) -> None:
        data = {
            "data": {
                "summary": "",
                "contact": {},
                "experiences": [],
                "educations": [],
                "skills": [],
                "languages": [],
            }
        }
        sections = resume_to_text(data, "pt-BR")
        c = assess_completeness(data, sections)
        self.assertEqual(c["level"], "insufficient")

    def test_analyze_sparse_resume_caps_scores(self) -> None:
        resume_data = {
            "data": {
                "summary": "Estudante",
                "contact": {},
                "experiences": [],
                "educations": [],
                "skills": [],
                "languages": [],
            }
        }
        result = analyze_resume(resume_data, job_description_text=None, language="pt-BR")
        self.assertLessEqual(result["score"], 45)
        self.assertEqual(result["task_scores"]["seniority"], 50)
        self.assertLessEqual(result["task_scores"]["ats"], 40)
        payload = result["payload_json"]
        self.assertEqual(payload["completeness"]["level"], "insufficient")
        self.assertEqual(payload["completeness"]["confidence"], "low")
        imp_keys = [i["key"] for i in payload["insights"]["improvements"]]
        self.assertIn("analysis.insights.improvements.fill_core_sections", imp_keys)
        self.assertNotIn(
            "analysis.insights.strengths.education_aligned",
            [s["key"] for s in payload["insights"]["strengths"]],
        )

    def test_intern_student_biology_vs_programador_is_realistic(self) -> None:
        resume_data = {
            "data": {
                "targetPosition": "Programador",
                "summary": "Estudante de biologia buscando oportunidades em desenvolvimento.",
                "contact": {},
                "experiences": [
                    {
                        "company": "Empresa X",
                        "position": "Estagiário de TI",
                        "description": ["Apoio em projeto por duas semanas."],
                    }
                ],
                "educations": [
                    {
                        "institution": "Universidade",
                        "course": "Biologia",
                        "degree": "Graduação em andamento",
                    }
                ],
                "skills": [],
                "languages": [],
            }
        }
        self.assertTrue(is_thin_student_or_intern_profile(resume_data))
        self.assertFalse(education_aligned_with_target(resume_data))
        result = analyze_resume(resume_data, job_description_text=None, language="pt-BR")
        self.assertEqual(result["task_scores"]["seniority"], 25)
        self.assertLessEqual(result["score"], 58)
        strengths = [s["key"] for s in result["payload_json"]["insights"]["strengths"]]
        self.assertNotIn("analysis.insights.strengths.education_aligned", strengths)
        imp = [i["key"] for i in result["payload_json"]["insights"]["improvements"]]
        self.assertIn("analysis.insights.improvements.education_target_gap", imp)

    def test_shallow_experience_without_intern_keyword_still_thin(self) -> None:
        """Cargo sem 'estágio' no título mas com pouquíssimo texto — mesmo perfil frágil."""
        resume_data = {
            "data": {
                "targetPosition": "Programador",
                "summary": "Buscando primeira oportunidade.",
                "contact": {},
                "experiences": [
                    {
                        "company": "Empresa",
                        "position": "Programador",
                        "description": ["Duas semanas de atividades."],
                    }
                ],
                "educations": [{"institution": "UF", "course": "Biologia", "degree": "Graduação"}],
                "skills": [],
                "languages": [],
            }
        }
        self.assertTrue(is_thin_student_or_intern_profile(resume_data))
        result = analyze_resume(resume_data, None, "pt-BR")
        self.assertEqual(result["task_scores"]["seniority"], 25)
        self.assertLessEqual(result["score"], 58)

    def test_junior_with_dates_not_treated_as_intern(self) -> None:
        """Uma experiência curta em texto mas ~2 anos em datas + cargo júnior → não é perfil de estágio."""
        resume_data = {
            "data": {
                "targetPosition": "Desenvolvedor Júnior",
                "summary": "Foco em APIs e qualidade de código.",
                "contact": {},
                "experiences": [
                    {
                        "company": "Tech Co",
                        "position": "Desenvolvedor Júnior",
                        "startDate": "2023-01-01",
                        "endDate": "2024-12-31",
                        "isCurrent": False,
                        "description": [
                            "Desenvolvimento de APIs REST.",
                            "Participação em code review.",
                        ],
                    }
                ],
                "educations": [
                    {"institution": "UF", "course": "Ciência da Computação", "degree": "Bacharelado"}
                ],
                "skills": [{"name": "Python"}, {"name": "Django"}, {"name": "PostgreSQL"}],
                "languages": [],
            }
        }
        self.assertFalse(is_thin_student_or_intern_profile(resume_data))
        self.assertEqual(structured_seniority_floor_lift(resume_data), "junior")
        result = analyze_resume(resume_data, None, "pt-BR")
        self.assertGreaterEqual(result["task_scores"]["seniority"], 50)

    def test_explicit_two_years_in_experience_lifts_thin_guard(self) -> None:
        """'2 anos' nas bullets (sem datas) ainda indica júnior, não estágio forçado."""
        resume_data = {
            "data": {
                "targetPosition": "Desenvolvedor",
                "summary": "Backend e integrações.",
                "contact": {},
                "experiences": [
                    {
                        "company": "Empresa",
                        "position": "Desenvolvedor",
                        "description": [
                            "2 anos construindo microsserviços e filas.",
                        ],
                    }
                ],
                "educations": [],
                "skills": [{"name": "Node.js"}, {"name": "PostgreSQL"}],
                "languages": [],
            }
        }
        self.assertFalse(is_thin_student_or_intern_profile(resume_data))
        result = analyze_resume(resume_data, None, "pt-BR")
        self.assertGreaterEqual(result["task_scores"]["seniority"], 50)

    def test_junior_two_years_in_summary_only_not_intern(self) -> None:
        """Texto típico de resumo (júnior + 2 anos) sem cargo de estágio."""
        resume_data = {
            "data": {
                "targetPosition": "Desenvolvedor Front-end",
                "summary": (
                    "Desenvolvedor júnior com 2 anos de experiência em desenvolvimento front-end."
                ),
                "contact": {},
                "experiences": [
                    {
                        "company": "Empresa",
                        "position": "Desenvolvedor Front-end",
                        "description": ["Componentes React e integração com APIs."],
                    }
                ],
                "educations": [],
                "skills": [{"name": "React"}, {"name": "TypeScript"}],
                "languages": [],
            }
        }
        self.assertGreaterEqual(max_years_mentioned_in_work_context(resume_data), 2)
        self.assertFalse(has_internship_position(resume_data))
        self.assertFalse(is_thin_student_or_intern_profile(resume_data))
        result = analyze_resume(resume_data, None, "pt-BR")
        self.assertGreaterEqual(result["task_scores"]["seniority"], 50)

    def test_two_plus_years_in_summary_detected(self) -> None:
        self.assertGreaterEqual(
            max_years_mentioned_in_work_context(
                {
                    "data": {
                        "targetPosition": "",
                        "summary": "Frontend com 2+ anos em produto.",
                        "experiences": [],
                    }
                }
            ),
            2,
        )

    def test_interno_in_position_is_not_internship(self) -> None:
        """'Interno' não deve acionar falso positivo de 'intern'."""
        resume_data = {
            "data": {
                "targetPosition": "Dev",
                "summary": "",
                "experiences": [
                    {
                        "company": "Banco",
                        "position": "Desenvolvedor Interno",
                        "description": ["Sistemas internos."],
                    }
                ],
            }
        }
        self.assertFalse(has_internship_position(resume_data))

    def test_years_in_resume_name_field(self) -> None:
        """Nome do CV (fora de data.*) também entra na leitura de 'N anos'."""
        self.assertGreaterEqual(
            max_years_mentioned_in_work_context(
                {
                    "name": "João — 2 anos em front-end",
                    "data": {"targetPosition": "", "summary": "", "experiences": []},
                }
            ),
            2,
        )

    @patch.object(orchestrator_mod, "is_thin_student_or_intern_profile", return_value=True)
    def test_structured_floor_lift_overrides_thin_intern_forcing(self, _mock: Any) -> None:
        """Mesmo com thin=True, '2 anos' + júnior no resumo deve subir para júnior (50)."""
        resume_data = {
            "data": {
                "targetPosition": "",
                "summary": "Desenvolvedor júnior com 2 anos de experiência em front-end.",
                "contact": {},
                "experiences": [],
                "educations": [],
                "skills": [],
                "languages": [],
            }
        }
        result = analyze_resume(resume_data, None, "pt-BR")
        self.assertGreaterEqual(result["task_scores"]["seniority"], 50)


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

    def test_target_position_exposes_target_fit_policy_metadata(self) -> None:
        resume_data = {
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
        result = analyze_resume(resume_data, None, "pt-BR")
        payload = result["payload_json"]
        self.assertIn("targetFitScore", payload)
        self.assertEqual(payload.get("targetFitProvider"), "target_fit_policy")
        self.assertIn("targetFitModelVersion", payload)
        meta = payload.get("model_metadata_by_task") or {}
        self.assertIn("target_fit", meta)
        self.assertEqual((meta.get("target_fit") or {}).get("provider"), "target_fit_policy")
        self.assertIsNotNone(result["task_scores"].get("target_fit"))

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
        self.assertIn(metadata_by_task["seniority"]["provider"], ("rule_policy", "signals_ml"))
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
