"""
Unit tests for analysis inference module.
"""
from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.analysis.application.inference.resume_mapper import resume_to_text
from apps.analysis.application.inference.safety import truncate_text
from apps.analysis.application.inference.postprocess.insights import derive_insights
from apps.analysis.application.inference.orchestrator import analyze_resume


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
