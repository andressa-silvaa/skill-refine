"""
Reading the resume's language from the document instead of the user's interface preference.

The preference is what ``worker.py`` passes in, and it is the language of the UI, not of the CV. The
detector overrides a stated user setting, so these cases are mostly about when it must *not*: short
or ambiguous text, an unsupported language, a missing bundle. Getting that wrong is worse than the
original bug, because it would override a correct preference with a confident guess.
"""
from __future__ import annotations

from django.test import SimpleTestCase, override_settings

from apps.analysis.application.inference.language_detection import (
    FALLBACK_PROVIDER,
    MIN_CONFIDENCE,
    PROVIDER,
    detect_language,
)

PT = (
    "Analista de dados com quatro anos de experiencia em modelagem dimensional, construcao de "
    "pipelines e relatorios executivos para as areas de negocio da empresa."
)
EN = (
    "Data analyst with four years of experience in dimensional modelling, building pipelines and "
    "executive reporting for the company's business units."
)


class _Pipeline:
    classes_ = ["en", "es", "pt"]

    def __init__(self, row):
        self._row = row

    def predict_proba(self, texts):
        return [self._row for _ in texts]


def _bundle(row):
    return {"pipeline": _Pipeline(row)}


class DetectorOverridesThePreferenceWhenSureTest(SimpleTestCase):
    def test_a_confident_answer_replaces_the_preference(self):
        lang, provider, confidence = detect_language(_bundle([0.97, 0.02, 0.01]), EN, "pt-BR")
        self.assertEqual(lang, "en-US")
        self.assertEqual(provider, PROVIDER)
        self.assertGreater(confidence, MIN_CONFIDENCE)

    def test_the_full_locale_tag_is_returned_not_the_bare_code(self):
        lang, _p, _c = detect_language(_bundle([0.01, 0.97, 0.02]), PT, "pt-BR")
        self.assertEqual(lang, "es-ES", "downstream keys off pt-BR/en-US/es-ES, not pt/en/es")

    def test_agreeing_with_the_preference_still_reports_the_model(self):
        lang, provider, _c = detect_language(_bundle([0.01, 0.02, 0.97]), PT, "pt-BR")
        self.assertEqual(lang, "pt-BR")
        self.assertEqual(provider, PROVIDER, "the provider names who decided, not whether it changed")


class DetectorDefersWhenItShouldTest(SimpleTestCase):
    def test_a_low_margin_answer_keeps_the_preference(self):
        lang, provider, confidence = detect_language(_bundle([0.36, 0.34, 0.30]), PT, "pt-BR")
        self.assertEqual(lang, "pt-BR")
        self.assertEqual(provider, FALLBACK_PROVIDER)
        self.assertLess(confidence, MIN_CONFIDENCE)

    def test_text_too_short_to_judge_keeps_the_preference(self):
        lang, provider, _c = detect_language(_bundle([0.99, 0.0, 0.01]), "Analista", "pt-BR")
        self.assertEqual(lang, "pt-BR")
        self.assertEqual(provider, FALLBACK_PROVIDER)

    def test_no_bundle_keeps_the_preference(self):
        lang, provider, _c = detect_language(None, EN, "pt-BR")
        self.assertEqual(lang, "pt-BR")
        self.assertEqual(provider, FALLBACK_PROVIDER)

    def test_an_unsupported_language_keeps_the_preference(self):
        class _French:
            classes_ = ["en", "fr", "pt"]

            def predict_proba(self, texts):
                return [[0.05, 0.90, 0.05] for _ in texts]

        lang, provider, _c = detect_language({"pipeline": _French()}, EN, "pt-BR")
        self.assertEqual(lang, "pt-BR", "the product answers in three languages; fr is not one")
        self.assertEqual(provider, FALLBACK_PROVIDER)

    def test_a_raising_pipeline_keeps_the_preference(self):
        class _Boom:
            classes_ = ["en", "es", "pt"]

            def predict_proba(self, texts):
                raise RuntimeError("boom")

        lang, provider, _c = detect_language({"pipeline": _Boom()}, EN, "pt-BR")
        self.assertEqual(lang, "pt-BR")
        self.assertEqual(provider, FALLBACK_PROVIDER)


@override_settings(
    ANALYSIS_LANGUAGE_DETECTION_ENABLED=True,
    ANALYSIS_EMBEDDINGS_ENABLED=False,
    ANALYSIS_ESCO_DOMAIN_ENABLED=False,
    ANALYSIS_LLM_FEEDBACK_ENABLED=False,
    ANALYSIS_REQUIRE_MODEL_ANSWER=False,
)
class ShippedDetectorReadsARealResumeTest(SimpleTestCase):
    """
    The artefact under ml/models, on an English resume submitted with a Portuguese preference — the
    exact production path that cost 17.4 points of domain accuracy.
    """

    def setUp(self):
        from django.conf import settings

        from apps.analysis.application.inference.config import get_config
        from apps.analysis.application.inference.language_detection import (
            clear_language_detector_cache,
            get_language_detector,
        )

        clear_language_detector_cache()
        self.bundle = get_language_detector(get_config(settings))
        if self.bundle is None:
            self.fail("language_detector bundle missing; every analysis would use the UI preference")

    def test_an_english_resume_is_not_analysed_as_portuguese(self):
        lang, provider, _c = detect_language(self.bundle, EN, "pt-BR")
        self.assertEqual(lang, "en-US")
        self.assertEqual(provider, PROVIDER)

    def test_a_portuguese_resume_stays_portuguese(self):
        lang, _p, _c = detect_language(self.bundle, PT, "pt-BR")
        self.assertEqual(lang, "pt-BR")

    def test_the_analysis_reports_who_chose_the_language(self):
        from apps.analysis.application.inference.orchestrator import analyze_resume

        resume = {
            "data": {
                "targetPosition": "Data Analyst",
                "summary": EN,
                "skills": [{"name": "SQL"}, {"name": "Python"}],
                "experiences": [
                    {
                        "position": "Data Analyst",
                        "company": "Acme",
                        "startDate": "2021-01",
                        "isCurrent": True,
                        "description": ["Built pipelines that cut monthly close time by 40%."],
                    }
                ],
                "educations": [{"institution": "State University", "course": "Statistics"}],
            }
        }
        payload = analyze_resume(resume, None, "pt-BR")["payload_json"]
        self.assertEqual(payload["analysisIntegrity"]["providersByTask"]["language"], PROVIDER)
