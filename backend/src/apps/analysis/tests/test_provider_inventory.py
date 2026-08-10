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
HEURISTIC_TASKS_TODAY = {"seniority", "quality"}
HEURISTIC_PROVIDERS = {"heuristics", "rule_policy", "target_fit_policy", "local"}

RESUME_TEXT = (
    "Analista de dados com seis anos de experiencia em modelagem e relatorios.\n"
    "Construi pipelines de dados e reduzi o tempo de fechamento mensal em 40%."
)
JOB_TEXT = "Vaga para analista de dados senior com SQL, Python e modelagem dimensional."


class _ConstantEncoder:
    """Every text maps to the same unit vector, so cosine is 1 and the step reports success."""

    def encode(self, texts, **kwargs):
        import numpy as np

        rows = [[1.0, 0.0, 0.0] for _ in texts]
        return np.asarray(rows, dtype=np.float32)


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
)
class ProviderInventoryTest(SimpleTestCase):
    """
    Embeddings on, because that is how production runs (backend/.env sets
    ANALYSIS_EMBEDDINGS_ENABLED=true). With them off, target_fit answers with its policy and the
    inventory below would understate how much is already neural.
    """

    def _analyze(self) -> dict:
        target = "apps.analysis.application.inference.orchestrator.get_embeddings_model"
        with mock.patch(target, return_value=_ConstantEncoder()):
            return analyze_resume(
                _well_formed_resume(), job_description_text=JOB_TEXT, language="pt-BR"
            )

    def test_matching_metadata_names_the_encoder_not_the_bundle(self):
        by_task = self._analyze()["payload_json"]["model_metadata_by_task"]
        self.assertEqual(by_task["matching"]["provider"], "matching_embeddings")
        self.assertEqual(by_task["matching"]["modelVersion"], "matching_embeddings_v1")
        self.assertNotEqual(by_task["matching"]["modelName"], "heuristics-only")

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
