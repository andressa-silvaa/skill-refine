"""
The per-bullet head that replaced METRICS_PATTERN, ACTION_VERBS and LEADERSHIP_WORDS.

Two kinds of test here, deliberately. The stubbed ones pin the contract — aggregation, the empty
case, and the refusal that keeps the regex in place — without depending on an artefact. The last
class runs the real bundle on the failures that motivated the swap, because a contract that holds
while the model answers wrongly is not the property worth protecting.
"""
from __future__ import annotations

from unittest import mock

from django.test import SimpleTestCase, override_settings

from apps.analysis.application.inference.tasks.quality.bullet_flags import (
    extract_bullets,
    predict_bullet_flags,
)
from apps.analysis.application.inference.tasks.quality.predict import (
    ACTION_VERBS,
    LEADERSHIP_WORDS,
    METRICS_PATTERN,
    predict_quality_detailed,
)


class _StubHead:
    def __init__(self, answers: list[bool]) -> None:
        self.answers = answers

    def predict(self, matrix):
        return list(self.answers)[: len(matrix)]


def _bundle(quantified: list[bool], outcome: list[bool], leadership: list[bool]) -> dict:
    return {
        "heads": {
            "quantified": _StubHead(quantified),
            "outcome": _StubHead(outcome),
            "leadership": _StubHead(leadership),
        }
    }


def _resume(bullets: list[str]) -> dict:
    return {"data": {"experiences": [{"position": "Analista", "description": bullets}]}}


class _IdentityEncoder:
    def encode(self, texts, **kwargs):
        import numpy as np

        return np.asarray([[1.0] + [0.0] * 383 for _ in texts], dtype=np.float32)


class BulletExtractionTest(SimpleTestCase):
    def test_blank_bullets_are_skipped(self):
        self.assertEqual(extract_bullets(_resume(["  ", "real one", ""])), ["real one"])

    def test_bullets_span_every_experience(self):
        resume = {
            "data": {
                "experiences": [
                    {"description": ["a"]},
                    {"description": ["b", "c"]},
                ]
            }
        }
        self.assertEqual(extract_bullets(resume), ["a", "b", "c"])

    def test_missing_or_malformed_payload_yields_nothing(self):
        self.assertEqual(extract_bullets(None), [])
        self.assertEqual(extract_bullets({}), [])
        self.assertEqual(extract_bullets({"data": {"experiences": ["not a dict"]}}), [])


class BulletFlagAggregationTest(SimpleTestCase):
    def test_one_positive_bullet_sets_the_document_flag(self):
        detail = predict_bullet_flags(
            _bundle([False, True], [False, False], [False, False]),
            _IdentityEncoder(),
            _resume(["duty only", "cut cost by 20%"]),
        )
        self.assertTrue(detail["flags"]["has_metrics"])
        self.assertFalse(detail["flags"]["has_action_verbs"])
        self.assertFalse(detail["flags"]["has_leadership"])
        self.assertEqual(detail["counts"]["quantified"], 1)
        self.assertEqual(detail["bullet_count"], 2)

    def test_a_resume_with_no_bullets_is_an_answer_not_a_failure(self):
        detail = predict_bullet_flags(_bundle([], [], []), _IdentityEncoder(), _resume([]))
        self.assertIsNotNone(detail)
        self.assertEqual(detail["bullet_count"], 0)
        self.assertEqual(
            detail["flags"],
            {"has_metrics": False, "has_action_verbs": False, "has_leadership": False},
        )

    def test_without_a_bundle_or_encoder_it_refuses_so_the_regex_stays(self):
        self.assertIsNone(predict_bullet_flags(None, _IdentityEncoder(), _resume(["x"])))
        self.assertIsNone(predict_bullet_flags(_bundle([], [], []), None, _resume(["x"])))

    def test_an_incomplete_bundle_refuses_rather_than_reporting_partial_flags(self):
        half = {"heads": {"quantified": _StubHead([True])}}
        self.assertIsNone(predict_bullet_flags(half, _IdentityEncoder(), _resume(["x"])))

    def test_a_head_that_raises_refuses_instead_of_publishing_empty_flags(self):
        class _Exploding:
            def predict(self, matrix):
                raise RuntimeError("boom")

        bundle = {"heads": {k: _Exploding() for k in ("quantified", "outcome", "leadership")}}
        self.assertIsNone(predict_bullet_flags(bundle, _IdentityEncoder(), _resume(["x"])))


class FlagProviderReportingTest(SimpleTestCase):
    """The response has to name which of the two answered, or the provider table stops being evidence."""

    def test_probe_answer_is_attributed_to_the_bullet_probe(self):
        _score, flags, detail = predict_quality_detailed(
            "texto",
            "pt-BR",
            None,
            resume_data=_resume(["Liderei um time de 5 pessoas."]),
            bullet_detail={
                "flags": {"has_metrics": True, "has_action_verbs": True, "has_leadership": True},
                "bullets": [],
                "bullet_count": 1,
                "counts": {"quantified": 1, "outcome": 1, "leadership": 1},
            },
            allow_heuristic_answer=True,
        )
        self.assertEqual(detail["flags_provider"], "bullet_probe")
        self.assertTrue(flags["has_leadership"])

    def test_without_the_probe_the_regex_answers_and_says_so(self):
        _score, _flags, detail = predict_quality_detailed(
            "texto sem nada",
            "pt-BR",
            None,
            resume_data=_resume(["Participei de reunioes."]),
            allow_heuristic_answer=True,
        )
        self.assertEqual(detail["flags_provider"], "heuristics")


@override_settings(
    ANALYSIS_EMBEDDINGS_ENABLED=True,
    ANALYSIS_BULLET_PROBE_ENABLED=True,
)
class RealBundleBeatsTheRegexTest(SimpleTestCase):
    """
    The bullets that motivated the swap, scored by the shipped artefact.

    Each one is a measured failure mode, not a hypothetical: LEADERSHIP_WORDS matches ``supervis``
    inside "supervisar la tensión" (voltage, not people) and ``gerenci``/``management`` inside a
    content-management system, while ACTION_VERBS is eight fixed word forms per language and so
    misses Spanish first-person preterite entirely — recall 0.03 on Spanish outcomes.

    Depends on ml/models/bullet_probe_v1 being present, like the provider inventory suite, because a
    missing artefact must fail loudly here rather than degrade silently in production.
    """

    CASES = (
        ("leadership", False, "Implemento un sistema de monitoreo remoto para supervisar la tension."),
        ("leadership", True, "Dirigi un equipo de seis tecnicos durante la instalacion."),
        ("leadership", False, "Built a content management system that cut review time."),
        ("outcome", True, "Redisene el sistema de distribucion, reduciendo la perdida en un 20%."),
        ("outcome", False, "Participei de reunioes semanais de alinhamento com a equipe."),
        ("quantified", True, "Realizei 20 sessoes de orientacao individual com estudantes."),
    )
    FLAG = {
        "quantified": "has_metrics",
        "outcome": "has_action_verbs",
        "leadership": "has_leadership",
    }
    LANG_OF = {"Implemento": "es", "Dirigi": "es", "Redisene": "es", "Built": "en"}

    def setUp(self):
        from django.conf import settings

        from apps.analysis.application.inference.config import get_config
        from apps.analysis.application.inference.tasks.quality.loader_bullet_probe import (
            clear_bullet_probe_cache,
            get_bullet_probe_bundle,
        )
        from apps.analysis.application.inference.tasks.target_fit.loader_embeddings import (
            get_embeddings_model,
        )

        clear_bullet_probe_cache()
        self.bundle = get_bullet_probe_bundle(get_config(settings))
        self.encoder = get_embeddings_model(settings)
        if self.bundle is None or self.encoder is None:
            self.fail("bullet_probe bundle or encoder missing; the swap would silently use regex")

    def _regex(self, attribute: str, text: str) -> bool:
        low = text.lower()
        lang = self.LANG_OF.get(text.split()[0], "pt")
        if attribute == "quantified":
            return bool(METRICS_PATTERN.search(low))
        if attribute == "leadership":
            return bool(LEADERSHIP_WORDS.search(low))
        return any(v in low for v in ACTION_VERBS[lang])

    def test_probe_is_right_where_the_regex_is_wrong(self):
        probe_right = regex_right = 0
        failures = []
        for attribute, expected, text in self.CASES:
            detail = predict_bullet_flags(self.bundle, self.encoder, _resume([text]))
            got = bool(detail["flags"][self.FLAG[attribute]])
            probe_right += got == expected
            regex_right += self._regex(attribute, text) == expected
            if got != expected:
                failures.append(f"{attribute}={got} (wanted {expected}) on {text!r}")
        self.assertEqual(probe_right, len(self.CASES), "; ".join(failures))
        self.assertLess(
            regex_right,
            probe_right,
            "these cases exist because the regex fails them; if it stopped failing, "
            "re-derive the baseline in ml/reports/bullet_regex_baseline_v3.md",
        )


@override_settings(
    ANALYSIS_EMBEDDINGS_ENABLED=True,
    ANALYSIS_BULLET_PROBE_ENABLED=True,
    ANALYSIS_QUALITY_PROBE_ENABLED=True,
    ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED=True,
    ANALYSIS_ESCO_DOMAIN_ENABLED=False,
    ANALYSIS_LLM_FEEDBACK_ENABLED=False,
)
class LeadershipSignalComesFromTheProbeTest(SimpleTestCase):
    """
    ``has_leadership_terms`` fed the seniority rule from a regex over the whole career blob, so a job
    title alone set it. It now carries the probe's reading of the described work.
    """

    def test_signal_follows_the_probe_not_the_job_title(self):
        from apps.analysis.application.inference.orchestrator import analyze_resume
        from apps.analysis.application.inference.tasks.quality.loader_bullet_probe import (
            clear_bullet_probe_cache,
        )

        clear_bullet_probe_cache()
        resume = {
            "data": {
                "targetPosition": "Gerente de Operacoes",
                "summary": "Profissional de operacoes com foco em processos e qualidade de entrega.",
                "skills": [{"name": "Excel"}, {"name": "SQL"}],
                "experiences": [
                    {
                        "position": "Gerente de Operacoes",
                        "company": "Empresa A",
                        "startDate": "2020-01",
                        "isCurrent": True,
                        "description": [
                            "Preenchi planilhas de controle diario de estoque.",
                            "Conferi notas fiscais recebidas pelo setor.",
                        ],
                    }
                ],
                "educations": [{"course": "Administracao", "degree": "Bacharelado"}],
            }
        }
        from apps.analysis.application.inference.signals import extract_resume_signals
        from apps.analysis.application.inference.resume_mapper import resume_to_text

        sections = resume_to_text(resume, language="pt-BR")

        self.assertTrue(
            LEADERSHIP_WORDS.search("gerente de operacoes"),
            "the premise of this test is that the regex fires on the title alone",
        )
        regex_answer = extract_resume_signals(resume, sections, language="pt-BR")
        self.assertTrue(regex_answer.has_leadership_terms)

        probe_answer = extract_resume_signals(
            resume, sections, language="pt-BR", leadership_override=False
        )
        self.assertFalse(
            probe_answer.has_leadership_terms,
            "the described work is stock spreadsheets and invoice checking, so the flag must be off "
            "once the probe reads the bullets instead of the title",
        )

        target = "apps.analysis.application.inference.orchestrator.get_embeddings_model"
        with mock.patch(target, return_value=_IdentityEncoder()):
            payload = analyze_resume(resume, job_description_text=None, language="pt-BR")[
                "payload_json"
            ]
        self.assertEqual(
            payload["analysisIntegrity"]["providersByTask"]["insight_flags"], "bullet_probe"
        )
