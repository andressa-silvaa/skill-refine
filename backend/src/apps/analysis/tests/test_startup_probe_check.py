"""
The startup check: a worker must not boot into a state where it answers with regex under a model's name.

This is the guard for the failure mode this project has paid for four times — a missing artefact
degrading in silence (handoff 5.7 and 9.7). Each time the code logged a warning per request and kept
answering, so nobody noticed until someone measured accuracy.

The check therefore runs once, at warmup, and by default raises. A crash-looping container is visible;
a warning in a log nobody tails is not.
"""
from __future__ import annotations

from contextlib import ExitStack
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from apps.analysis.application.inference.config import get_config
from apps.analysis.application.inference.warmup import (
    ProbeBundleMissing,
    prewarm_analysis_models,
    verify_enabled_probes,
)

WARMUP = "apps.analysis.application.inference.warmup"


class VerifyEnabledProbesTest(SimpleTestCase):
    @override_settings(
        ANALYSIS_QUALITY_PROBE_ENABLED=False,
        ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED=False,
        ANALYSIS_EMBEDDINGS_ENABLED=False,
    )
    def test_nothing_to_check_when_no_probe_is_enabled(self):
        self.assertEqual(verify_enabled_probes(get_config(settings)), [])

    @override_settings(
        ANALYSIS_QUALITY_PROBE_ENABLED=True,
        ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED=False,
        ANALYSIS_EMBEDDINGS_ENABLED=False,
    )
    def test_probe_without_the_encoder_is_reported(self):
        problems = verify_enabled_probes(get_config(settings))
        self.assertTrue(any("ANALYSIS_EMBEDDINGS_ENABLED" in p for p in problems))

    @override_settings(
        ANALYSIS_QUALITY_PROBE_ENABLED=True,
        ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED=True,
        ANALYSIS_EMBEDDINGS_ENABLED=True,
    )
    def test_missing_bundles_are_reported_per_probe(self):
        with mock.patch(f"{WARMUP}.get_embeddings_model", return_value=object()), mock.patch(
            f"{WARMUP}.get_quality_probe_bundle", return_value=None
        ), mock.patch(f"{WARMUP}.get_seniority_probe_bundle", return_value=None):
            problems = verify_enabled_probes(get_config(settings))
        self.assertTrue(any("quality_probe" in p for p in problems))
        self.assertTrue(any("text_seniority_probe" in p for p in problems))

    @override_settings(
        ANALYSIS_QUALITY_PROBE_ENABLED=True,
        ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED=True,
        ANALYSIS_EMBEDDINGS_ENABLED=True,
    )
    def test_loaded_bundles_report_no_problem(self):
        with mock.patch(f"{WARMUP}.get_embeddings_model", return_value=object()), mock.patch(
            f"{WARMUP}.get_quality_probe_bundle", return_value={"heads": {}}
        ), mock.patch(f"{WARMUP}.get_seniority_probe_bundle", return_value={"heads": {}}):
            self.assertEqual(verify_enabled_probes(get_config(settings)), [])


@override_settings(
    ANALYSIS_PREWARM_LANGUAGES="pt-BR",
    ANALYSIS_QUALITY_PROBE_ENABLED=True,
    ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED=True,
    ANALYSIS_EMBEDDINGS_ENABLED=True,
    ANALYSIS_ESCO_DOMAIN_ENABLED=False,
)
class PrewarmFailFastTest(SimpleTestCase):
    @staticmethod
    def _stack(*, probes_load: bool) -> ExitStack:
        """Stub every loader warmup touches, so the test isolates the probe check itself."""
        bundle = {"heads": {}} if probes_load else None
        stack = ExitStack()
        for target, value in (
            ("get_model_bundle", (None, {})),
            ("get_quality_bundle", (None, {})),
            ("get_matching_bundle", (None, {})),
            ("get_embeddings_model", object()),
            ("get_quality_probe_bundle", bundle),
            ("get_seniority_probe_bundle", bundle),
        ):
            stack.enter_context(mock.patch(f"{WARMUP}.{target}", return_value=value))
        return stack

    @override_settings(ANALYSIS_FAIL_FAST_ON_MISSING_BUNDLE=True)
    def test_prewarm_raises_when_a_bundle_is_missing(self):
        with self._stack(probes_load=False):
            with self.assertRaises(ProbeBundleMissing) as caught:
                prewarm_analysis_models()
        message = str(caught.exception)
        self.assertIn("quality_probe", message)
        self.assertIn("ANALYSIS_FAIL_FAST_ON_MISSING_BUNDLE", message)

    @override_settings(ANALYSIS_FAIL_FAST_ON_MISSING_BUNDLE=False)
    def test_prewarm_continues_when_fail_fast_is_off(self):
        with self._stack(probes_load=False):
            prewarm_analysis_models()

    @override_settings(ANALYSIS_FAIL_FAST_ON_MISSING_BUNDLE=True)
    def test_prewarm_is_quiet_when_everything_loads(self):
        with self._stack(probes_load=True):
            prewarm_analysis_models()
