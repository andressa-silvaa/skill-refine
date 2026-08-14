"""Regression tests: text sanitization, seniority fusion, quality spread, optional embedding fit."""
from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.analysis.application.inference.orchestrator import analyze_resume
from apps.analysis.application.inference.text_sanitizer import resume_to_text_sanitized
from apps.analysis.application.inference.loader import _metadata_supports_task
from apps.analysis.application.inference.tasks.seniority.text.fuse_seniority import fuse_seniority
from apps.analysis.application.inference.tasks.seniority.text.predict import predict_text_seniority


class TextSanitizerTests(TestCase):
    def test_strips_email_and_truncates(self) -> None:
        data = {
            "data": {
                "summary": "Dev contato@mail.com " + ("x " * 900),
                "targetPosition": "Engenheiro",
                "experiences": [{"title": "Lead"}],
                "educations": [{"course": "CS"}],
                "skills": [{"name": "Python"}],
            }
        }
        out = resume_to_text_sanitized(data, max_chars=200)
        self.assertNotIn("contato@", out)
        self.assertLessEqual(len(out), 220)


class TextSeniorityFusionTests(TestCase):
    def test_lexical_senior_summary_fuses_to_senior_with_weak_signals(self) -> None:
        text = (
            "Desenvolvedor sênior full-stack com 10 anos de experiência, "
            "líder de tecnologia em produtos digitais."
        )
        pred = predict_text_seniority(text, "pt-BR", None, allow_lexical_fallback=True)
        self.assertEqual(pred.get("label"), "senior")
        fused_label, conf, meta = fuse_seniority(
            "mid",
            "low",
            pred.get("label"),
            str(pred.get("confidence") or "low"),
            0.05,
            has_leadership_terms=False,
            total_months_experience=0,
            text_suggests_senior=True,
        )
        self.assertEqual(fused_label, "senior")
        self.assertIn(conf, ("high", "medium", "low"))
        self.assertEqual(meta.get("fusion"), "signals_ml_text")


# Exercises the fallback path on purpose: these assertions are about completeness caps, thin-
# profile guards, insights, target_fit and persistence — not about the quality model. Production
# refuses a heuristic quality score (ANALYSIS_REQUIRE_MODEL_ANSWER defaults on), so the flag is
# turned off here rather than left to a suite-wide default that would hide the policy.
@override_settings(ANALYSIS_REQUIRE_MODEL_ANSWER=False)
class OrchestratorSeniorityLexicalTests(TestCase):
    @override_settings(
        ANALYSIS_SIGNALS_ML_ENABLED=False,
        ANALYSIS_TEXT_SENIORITY_ENABLED=False,
        ANALYSIS_TEXT_SENIORITY_FUSION_ENABLED=True,
    )
    def test_senior_from_summary_without_dates(self) -> None:
        resume_data = {
            "data": {
                "summary": (
                    "Desenvolvedor sênior full-stack com 10 anos de experiência. "
                    "Líder de tecnologia em times de produto."
                ),
                "contact": {},
                "experiences": [],
                "educations": [],
                "skills": [{"name": "Python"}],
                "languages": [],
            }
        }
        result = analyze_resume(resume_data, None, "pt-BR")
        self.assertEqual(result.get("seniority_final_label"), "senior")
        self.assertEqual(result.get("seniority_label_source"), "fused")


# Exercises the fallback path on purpose: these assertions are about completeness caps, thin-
# profile guards, insights, target_fit and persistence — not about the quality model. Production
# refuses a heuristic quality score (ANALYSIS_REQUIRE_MODEL_ANSWER defaults on), so the flag is
# turned off here rather than left to a suite-wide default that would hide the policy.
@override_settings(ANALYSIS_REQUIRE_MODEL_ANSWER=False)
class OverallScoreVariationTests(TestCase):
    def test_scores_differ_across_distinct_resumes(self) -> None:
        sparse = {
            "data": {
                "summary": "",
                "contact": {},
                "experiences": [],
                "educations": [],
                "skills": [],
                "languages": [],
            }
        }
        rich = {
            "data": {
                "summary": (
                    "Engenheiro backend. Implementei APIs REST em Python e Django, "
                    "reduzi latência em 22% e liderei squad de 4 pessoas. "
                    "github.com/foo portfolio."
                ),
                "contact": {},
                "experiences": [
                    {
                        "company": "Acme",
                        "position": "Backend Engineer",
                        "description": ["Python", "Django", "PostgreSQL", "Kubernetes", "métricas e SLOs."],
                    }
                ],
                "educations": [{"course": "Computer Science"}],
                "skills": [{"name": "Python"}, {"name": "Django"}, {"name": "PostgreSQL"}],
                "languages": [],
            },
        }
        a = analyze_resume(sparse, None, "pt-BR")["score"]
        b = analyze_resume(rich, None, "pt-BR")["score"]
        self.assertNotEqual(a, b)


# Exercises the fallback path on purpose: these assertions are about completeness caps, thin-
# profile guards, insights, target_fit and persistence — not about the quality model. Production
# refuses a heuristic quality score (ANALYSIS_REQUIRE_MODEL_ANSWER defaults on), so the flag is
# turned off here rather than left to a suite-wide default that would hide the policy.
@override_settings(ANALYSIS_REQUIRE_MODEL_ANSWER=False)
class EmbeddingTargetFitPatchTests(TestCase):
    @override_settings(ANALYSIS_EMBEDDINGS_ENABLED=True, ANALYSIS_TARGET_FIT_EMBED_WEIGHT=1.0)
    @patch(
        "apps.analysis.application.inference.resolve_target_fit.embedding_fit_scores",
        return_value=(88, 0.91, ["python", "stack"]),
    )
    @patch("apps.analysis.application.inference.orchestrator.get_embeddings_model")
    def test_target_fit_above_70_when_embedding_returns_high(
        self, mock_get_emb, _mock_scores
    ) -> None:
        mock_get_emb.return_value = object()
        resume_data = {
            "data": {
                "targetPosition": "Desenvolvedor full-stack sênior",
                "summary": "Full-stack developer senior Python React 10 years.",
                "contact": {},
                "experiences": [{"company": "X", "position": "Senior Developer", "description": ["APIs"]}],
                "educations": [],
                "skills": [{"name": "Python"}, {"name": "React"}],
                "languages": [],
            }
        }
        result = analyze_resume(resume_data, None, "en-US")
        self.assertGreaterEqual(result["payload_json"].get("targetFitScore", 0), 70)
        self.assertEqual(result["payload_json"].get("targetFitProvider"), "target_fit_embedding_v1")


class LoaderMetadataTaskTests(TestCase):
    def test_text_seniority_metadata_matches_seniority_bundle(self) -> None:
        self.assertTrue(_metadata_supports_task({"task": "text_seniority"}, "seniority"))
        self.assertFalse(_metadata_supports_task({"task": "text_seniority"}, "quality"))
