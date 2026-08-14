"""
Which step actually answered each task, and whether telemetry says so.

The provider table is the evidence that the analysis is model-driven, so a wrong provider is a
reporting bug with the same weight as a wrong score.
"""
from __future__ import annotations

from unittest import mock

from django.test import SimpleTestCase, override_settings

from apps.analysis.application.inference.orchestrator import analyze_resume
from apps.analysis.application.inference.tasks.matching.predict import predict_matching_detailed

# Tasks whose answer still comes from a rule or a regex. Every entry removed from this set is a
# pillar that became model-driven; see docs/analysis/HANDOFF_ml_pipeline.md section 7.
#
# Emptied when the embedding probes shipped: `seniority` is answered by `text_seniority_probe`,
# `quality` by `quality_probe`, and `insight_flags` — the per-bullet facts that pick which strengths
# and improvements are shown — by `bullet_probe`. All are linear heads over the frozen multilingual
# encoder. The rule policy, `_heuristic_score` and the three regex families remain in the cascade
# *behind* them, which is the only role the project allows a heuristic to hold.
HEURISTIC_TASKS_TODAY: set[str] = set()
HEURISTIC_PROVIDERS = {"heuristics", "rule_policy", "target_fit_policy", "local"}

RESUME_TEXT = (
    "Analista de dados com seis anos de experiencia em modelagem e relatorios.\n"
    "Construi pipelines de dados e reduzi o tempo de fechamento mensal em 40%."
)
JOB_TEXT = "Vaga para analista de dados senior com SQL, Python e modelagem dimensional."


ENCODER_DIM = 384


class _ConstantEncoder:
    """
    Every text maps to the same unit vector, so cosine is 1 and every encoder step reports success.

    The width has to be the real encoder's 384, not a toy 3: the probes concatenate one vector per
    resume section plus one for the document, and their loader refuses a row whose width does not
    match the bundle. A narrower stub would make the probes skip and the inventory below would go on
    reporting heuristics — passing for the wrong reason.
    """

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
                "construcao de pipelines e relatorios executivos para areas de negocio."
            ),
            "contact": {"linkedin": "https://linkedin.com/in/exemplo"},
            "skills": [{"name": "SQL"}, {"name": "Python"}, {"name": "Power BI"}, {"name": "dbt"}],
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
                        "Automatizei relatorios recorrentes economizando 12 horas por mes.",
                        "Modelei indicadores de churn usados pela diretoria comercial.",
                        "Documentei o dicionario de dados de nove fontes.",
                    ],
                },
            ],
            "educations": [
                {"course": "Estatistica", "degree": "Graduacao", "institution": "Universidade X"}
            ],
        }
    }


class MatchingProviderTest(SimpleTestCase):
    def test_encoder_answer_is_reported_as_embeddings(self):
        score, _top, provider = predict_matching_detailed(
            RESUME_TEXT, JOB_TEXT, "pt-BR", matching_bundle=None, embeddings_model=_ConstantEncoder()
        )
        self.assertEqual(provider, "matching_embeddings")
        self.assertGreater(score, 0)

    def test_without_encoder_the_provider_is_heuristics(self):
        _score, _top, provider = predict_matching_detailed(
            RESUME_TEXT, JOB_TEXT, "pt-BR", matching_bundle=None, embeddings_model=None
        )
        self.assertEqual(provider, "heuristics")

    def test_no_input_is_not_reported_as_a_provider(self):
        score, top, provider = predict_matching_detailed("", JOB_TEXT, "pt-BR")
        self.assertEqual((score, top), (0, []))
        self.assertEqual(provider, "skipped_no_input")


@override_settings(
    ANALYSIS_EMBEDDINGS_ENABLED=True,
    ANALYSIS_ESCO_DOMAIN_ENABLED=False,
    ANALYSIS_LLM_FEEDBACK_ENABLED=False,
    ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED=True,
    ANALYSIS_QUALITY_PROBE_ENABLED=True,
    ANALYSIS_BULLET_PROBE_ENABLED=True,
    ANALYSIS_INSIGHT_RANKING_ENABLED=True,
)
class ProviderInventoryTest(SimpleTestCase):
    """
    Embeddings and all three probes on, because that is how production runs (docker-compose sets
    them). With embeddings off, target_fit answers with its policy; with the probes off, seniority
    and quality answer with a rule and the insight flags answer with regex — and the inventory below
    would understate how much is neural.

    This suite depends on the bundles under ml/models/ being present. That is deliberate: the whole
    point of the inventory is that a missing artefact must fail loudly here rather than degrade
    silently in production.
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
                _well_formed_resume(), job_description_text=JOB_TEXT, language="pt-BR"
            )

    def test_seniority_is_answered_by_the_text_probe(self):
        by_task = self._analyze()["payload_json"]["model_metadata_by_task"]
        self.assertEqual(by_task["seniority"]["provider"], "text_seniority_probe")

    def test_quality_is_answered_by_the_probe(self):
        by_task = self._analyze()["payload_json"]["model_metadata_by_task"]
        self.assertEqual(by_task["quality"]["provider"], "quality_probe")

    def test_matching_metadata_names_the_encoder_not_the_bundle(self):
        by_task = self._analyze()["payload_json"]["model_metadata_by_task"]
        self.assertEqual(by_task["matching"]["provider"], "matching_embeddings")
        self.assertEqual(by_task["matching"]["modelVersion"], "matching_embeddings_v1")
        self.assertNotEqual(by_task["matching"]["modelName"], "heuristics-only")

    def test_insight_flags_are_answered_by_the_bullet_probe(self):
        by_task = self._analyze()["payload_json"]["model_metadata_by_task"]
        self.assertEqual(by_task["insight_flags"]["provider"], "bullet_probe")

    def test_insight_order_comes_from_the_measured_gain_table(self):
        by_task = self._analyze()["payload_json"]["model_metadata_by_task"]
        self.assertEqual(by_task["insight_ranking"]["provider"], "insight_gain_v1")

    def test_target_fit_is_answered_by_the_encoder(self):
        by_task = self._analyze()["payload_json"]["model_metadata_by_task"]
        self.assertEqual(by_task["target_fit"]["provider"], "target_fit_embedding_v1")

    def test_only_the_documented_tasks_answer_with_a_heuristic(self):
        """
        Failing here is good news twice over: either a task became model-driven and the set must
        shrink, or a task silently fell back to a heuristic when it should not have.
        """
        by_task = self._analyze()["payload_json"]["model_metadata_by_task"]
        heuristic = {
            task
            for task, meta in by_task.items()
            if str(meta.get("provider") or "") in HEURISTIC_PROVIDERS
        }
        self.assertEqual(
            heuristic,
            HEURISTIC_TASKS_TODAY,
            "provider inventory changed: update HEURISTIC_TASKS_TODAY and the roadmap in "
            "docs/analysis/HANDOFF_ml_pipeline.md section 7",
        )
