"""
Completude, guarda de perfil raso e os caps: o que a analise faz com curriculo pouco preenchido.

Separado de ``test_inference.py`` porque e o bloco maior dela e tem assunto proprio.
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
