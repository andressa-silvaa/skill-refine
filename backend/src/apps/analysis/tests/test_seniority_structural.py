"""Unit tests: structured signals + rule-based seniority (no HF load)."""
from __future__ import annotations

from django.test import TestCase

from apps.analysis.application.inference.resume_mapper import resume_to_text
from apps.analysis.application.inference.seniority.rule_based import rule_based_seniority
from apps.analysis.application.inference.signals import extract_resume_signals


class ExtractResumeSignalsTest(TestCase):
    def test_empty_resume_insufficient(self) -> None:
        rd = {"data": {"summary": "", "experiences": [], "educations": [], "skills": [], "languages": [], "contact": {}}}
        sections = resume_to_text(rd, "pt-BR")
        s = extract_resume_signals(rd, sections, "pt-BR")
        self.assertEqual(s.experiences_count, 0)
        self.assertTrue(s.insufficient_data)

    def test_merge_months_two_jobs(self) -> None:
        rd = {
            "data": {
                "summary": "Dev",
                "experiences": [
                    {
                        "company": "A",
                        "position": "Dev",
                        "startDate": "2020-01-01",
                        "endDate": "2021-12-31",
                        "isCurrent": False,
                        "description": ["x"],
                    },
                    {
                        "company": "B",
                        "position": "Dev",
                        "startDate": "2022-01-01",
                        "endDate": "2024-12-31",
                        "isCurrent": False,
                        "description": ["y"],
                    },
                ],
                "educations": [],
                "skills": [{"name": "Python"}],
                "languages": [],
                "contact": {},
            }
        }
        sections = resume_to_text(rd, "pt-BR")
        s = extract_resume_signals(rd, sections, "pt-BR")
        self.assertGreaterEqual(s.total_months_experience, 48)


class RuleBasedSeniorityTest(TestCase):
    def _sig(self, **kwargs):
        from apps.analysis.application.inference.signals.types import ResumeSignals

        defaults = dict(
            total_months_experience=0,
            effective_months_experience=0,
            experiences_count=0,
            bullets_count=0,
            has_current_role=False,
            months_in_current_role=0,
            has_internship_terms=False,
            has_leadership_terms=False,
            has_links=False,
            summary_char_count=0,
            skills_count=0,
            education_present=False,
            completeness_score=50,
            completeness_level="low",
            insufficient_data=True,
            reasons=(),
            word_count=10,
            language="pt-BR",
        )
        defaults.update(kwargs)
        return ResumeSignals(**defaults)

    def test_no_experience_max_junior(self) -> None:
        label, conf, _ = rule_based_seniority(self._sig())
        self.assertEqual(label, "junior")
        self.assertEqual(conf, "low")

    def test_senior_requires_bullets(self) -> None:
        label, _, ev = rule_based_seniority(
            self._sig(
                experiences_count=3,
                effective_months_experience=70,
                total_months_experience=70,
                bullets_count=3,
                insufficient_data=False,
                completeness_level="adequate",
                completeness_score=80,
            )
        )
        self.assertEqual(label, "mid")
        self.assertTrue(any(e.get("rule") == "senior_months_insufficient_evidence" for e in ev))


class MlAdjustStubTest(TestCase):
    """ml_adjust without loading torch — bundle None."""

    def test_skips_when_no_model(self) -> None:
        from apps.analysis.application.inference.seniority.ml_adjust import ml_adjust_seniority
        from apps.analysis.application.inference.signals.types import ResumeSignals

        s = ResumeSignals(
            total_months_experience=6,
            effective_months_experience=6,
            experiences_count=1,
            bullets_count=2,
            has_current_role=False,
            months_in_current_role=0,
            has_internship_terms=False,
            has_leadership_terms=False,
            has_links=False,
            summary_char_count=40,
            skills_count=2,
            education_present=True,
            completeness_score=80,
            completeness_level="adequate",
            insufficient_data=False,
            reasons=(),
            word_count=120,
            language="pt-BR",
        )
        fl, conf, _, status = ml_adjust_seniority(
            "x" * 200,
            "pt-BR",
            "intern",
            "medium",
            [],
            s,
            (None, {"provider": "heuristics-only"}),
            allow_ml=True,
        )
        self.assertEqual(status, "skipped_no_model")
        self.assertEqual(fl, "intern")
