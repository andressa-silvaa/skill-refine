"""
The refusal policy: a heuristic may no longer answer for quality, and a rule answer must say so.

These tests guard the decision argued in docs/analysis/HANDOFF_ml_pipeline.md section 9.8. The
measurement behind it: `_heuristic_score` averages 41.4 / 52.4 / 57.8 on resumes planted as poor /
fair / good, so as a fallback for 78% of the score it carries almost no information — while being
indistinguishable on screen from a model's answer. Refusing is the honest outcome.

What must never regress:

1. quality refuses rather than publishing a heuristic score, and the refusal is a typed exception the
   worker can turn into an actionable message.
2. the refusal is switchable, because the golden snapshot suite needs the fallback path to stay alive.
3. seniority is allowed to answer with the rule, but the response is always marked degraded.
4. an analysis answered entirely by models reports itself as not degraded — otherwise the flag is
   decoration rather than a check.
"""
from __future__ import annotations

from unittest import mock

from django.test import SimpleTestCase, override_settings

from apps.analysis.application.inference.integrity import (
    ModelAnswerRequired,
    build_integrity_block,
    is_heuristic,
)
from apps.analysis.application.inference.orchestrator import analyze_resume
from apps.analysis.application.inference.tasks.quality.predict import predict_quality_detailed

ENCODER_DIM = 384


class _ConstantEncoder:
    """Real width, constant direction: enough for the probes to load and answer."""

    def encode(self, texts, **kwargs):
        import numpy as np

        row = [1.0] + [0.0] * (ENCODER_DIM - 1)
        return np.asarray([row for _ in texts], dtype=np.float32)


def _well_formed_resume() -> dict:
    return {
        "data": {
            "targetPosition": "Analista de Dados Senior",
            "summary": (
                "Analista de dados com seis anos de experiencia em modelagem dimensional, "
                "construcao de pipelines e relatorios executivos."
            ),
            "contact": {"linkedin": "https://linkedin.com/in/exemplo"},
            "skills": [{"name": "SQL"}, {"name": "Python"}, {"name": "dbt"}],
            "experiences": [
                {
                    "position": "Analista de Dados Senior",
                    "company": "Empresa A",
                    "startDate": "2021-01",
                    "endDate": "",
                    "isCurrent": True,
                    "description": [
                        "Construi pipelines que reduziram o fechamento mensal em 40%.",
                        "Coordenei tres analistas na migracao do modelo dimensional.",
                        "Implementei testes de qualidade que cortaram retrabalho em 25%.",
                    ],
                },
                {
                    "position": "Analista de Dados",
                    "company": "Empresa B",
                    "startDate": "2018-03",
                    "endDate": "2020-12",
                    "isCurrent": False,
                    "description": [
                        "Automatizei relatorios economizando 12 horas por mes.",
                        "Modelei indicadores de churn usados pela diretoria.",
                        "Documentei o dicionario de dados de nove fontes.",
                    ],
                },
            ],
            "educations": [{"course": "Estatistica", "institution": "Universidade X"}],
        }
    }


class IntegrityHelpersTest(SimpleTestCase):
    def test_known_rule_providers_count_as_heuristic(self):
        for provider in ("heuristics", "heuristics-only", "rule_policy", "target_fit_policy"):
            self.assertTrue(is_heuristic(provider), provider)

    def test_model_providers_do_not_count_as_heuristic(self):
        for provider in ("quality_probe", "text_seniority_probe", "target_fit_embedding_v1"):
            self.assertFalse(is_heuristic(provider), provider)

    def test_block_names_every_degraded_task(self):
        block = build_integrity_block(
            {"quality": "quality_probe", "seniority": "rule_policy", "target_fit": "target_fit_policy"}
        )
        self.assertTrue(block["degraded"])
        self.assertEqual(block["degradedTasks"], ["seniority", "target_fit"])
        self.assertIn("rule", block["reason"])

    def test_block_is_clean_when_every_pillar_is_a_model(self):
        block = build_integrity_block({"quality": "quality_probe", "seniority": "text_seniority_probe"})
        self.assertFalse(block["degraded"])
        self.assertEqual(block["degradedTasks"], [])
        self.assertEqual(block["reason"], "")


class QualityRefusesHeuristicAnswerTest(SimpleTestCase):
    """The predictor itself, without the orchestrator, so the contract is pinned at the source."""

    def test_returns_no_score_when_probe_missing(self):
        score, flags, detail = predict_quality_detailed(
            "Analista de dados com seis anos de experiencia e 40% de ganho.",
            "pt-BR",
            None,
            probe_bundle=None,
            embeddings_model=None,
            allow_heuristic_answer=False,
        )
        self.assertIsNone(score)
        self.assertEqual(detail["provider"], "no_model")
        self.assertIn("reason", detail)

    def test_flags_survive_the_refusal(self):
        """derive_insights reads these, so refusing a score must not blank them."""
        _score, flags, _detail = predict_quality_detailed(
            "Reduzi custo em 30% e publiquei em github.com/exemplo.",
            "pt-BR",
            None,
            probe_bundle=None,
            embeddings_model=None,
            allow_heuristic_answer=False,
        )
        self.assertTrue(flags["has_metrics"])
        self.assertTrue(flags["has_links"])

    def test_heuristic_answers_when_explicitly_allowed(self):
        score, _flags, detail = predict_quality_detailed(
            "Reduzi custo em 30% e publiquei em github.com/exemplo.",
            "pt-BR",
            None,
            probe_bundle=None,
            embeddings_model=None,
            allow_heuristic_answer=True,
        )
        self.assertIsNotNone(score)
        self.assertEqual(detail["provider"], "heuristics")


@override_settings(
    ANALYSIS_EMBEDDINGS_ENABLED=False,
    ANALYSIS_QUALITY_PROBE_ENABLED=False,
    ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED=False,
    ANALYSIS_ESCO_DOMAIN_ENABLED=False,
    ANALYSIS_LLM_FEEDBACK_ENABLED=False,
)
class OrchestratorRefusalTest(SimpleTestCase):
    @override_settings(ANALYSIS_REQUIRE_MODEL_ANSWER=True)
    def test_analysis_raises_instead_of_scoring_with_regex(self):
        with self.assertRaises(ModelAnswerRequired) as caught:
            analyze_resume(_well_formed_resume(), job_description_text=None, language="pt-BR")
        self.assertEqual(caught.exception.task, "quality")
        message = str(caught.exception)
        self.assertIn("ANALYSIS_QUALITY_PROBE_ENABLED", message)

    @override_settings(ANALYSIS_REQUIRE_MODEL_ANSWER=False)
    def test_fallback_still_works_when_the_policy_is_off(self):
        result = analyze_resume(_well_formed_resume(), job_description_text=None, language="pt-BR")
        integrity = result["payload_json"]["analysisIntegrity"]
        self.assertTrue(integrity["degraded"])
        self.assertIn("quality", integrity["degradedTasks"])
        self.assertIsNotNone(result["score"])


@override_settings(
    ANALYSIS_EMBEDDINGS_ENABLED=True,
    ANALYSIS_QUALITY_PROBE_ENABLED=True,
    ANALYSIS_BULLET_PROBE_ENABLED=True,
    ANALYSIS_INSIGHT_RANKING_ENABLED=True,
    ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED=False,
    ANALYSIS_REQUIRE_MODEL_ANSWER=True,
    ANALYSIS_ESCO_DOMAIN_ENABLED=False,
    ANALYSIS_LLM_FEEDBACK_ENABLED=False,
)
class SeniorityDegradedModeTest(SimpleTestCase):
    """
    Quality has its probe, seniority does not. Seniority may still answer — the rule reaches 70.4%
    against the probe's 75.9% — but the response has to admit it.

    The bullet probe is on so that seniority is the *only* degraded task: with it off, the flags that
    drive the insight copy fall back to regex and appear in ``degradedTasks`` too, which is correct
    behaviour but would stop this test from isolating what it is about.
    """

    def setUp(self):
        from apps.analysis.application.inference.tasks.quality.loader_bullet_probe import (
            clear_bullet_probe_cache,
        )
        from apps.analysis.application.inference.tasks.quality.loader_quality_probe import (
            clear_quality_probe_cache,
        )
        from apps.analysis.application.inference.tasks.seniority.text.loader_seniority_probe import (
            clear_seniority_probe_cache,
        )

        from apps.analysis.application.inference.postprocess.insight_ranking import (
            clear_gain_cache,
        )

        clear_bullet_probe_cache()
        clear_gain_cache()
        clear_quality_probe_cache()
        clear_seniority_probe_cache()

    def _analyze(self) -> dict:
        target = "apps.analysis.application.inference.orchestrator.get_embeddings_model"
        with mock.patch(target, return_value=_ConstantEncoder()):
            return analyze_resume(
                _well_formed_resume(), job_description_text=None, language="pt-BR"
            )

    def test_seniority_answers_with_the_rule_and_is_marked_degraded(self):
        payload = self._analyze()["payload_json"]
        by_task = payload["model_metadata_by_task"]
        self.assertEqual(by_task["seniority"]["provider"], "rule_policy")
        self.assertEqual(by_task["quality"]["provider"], "quality_probe")

        integrity = payload["analysisIntegrity"]
        self.assertTrue(integrity["degraded"])
        self.assertEqual(integrity["degradedTasks"], ["seniority"])
        self.assertEqual(integrity["providersByTask"]["quality"], "quality_probe")

    def test_degraded_seniority_does_not_blend_with_the_lexical_guesser(self):
        """
        Fusion lost to both of its own inputs against the human verdicts (58.7% vs 67.4%), so the
        degraded answer must be the rule alone and attributable to it.
        """
        payload = self._analyze()["payload_json"]
        sources = {
            str(item.get("source"))
            for item in payload.get("seniorityEvidence") or []
            if isinstance(item, dict)
        }
        self.assertNotIn("lexical", sources)
