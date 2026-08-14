"""
Low-confidence marking on the quality head, and the refusal message when the head is never consulted.

Two guards that are easy to confuse and cover different failures:

* ``LOW_CONFIDENCE_MARGIN`` — the head answered, but its margin puts the answer among the ones it
  tends to get wrong. Measured: withholding confidence from the lowest-margin 10% takes accuracy from
  92.9% to 96.5% over 691 labelled resumes.
* the completeness gate — the input is degenerate and the head is *confidently* wrong on it (an empty
  resume scores 78 at margin 0.368), so no uncertainty measure would catch it.

These cases pin the wiring and the messages, not the threshold value, which moves with the corpus.
"""
from __future__ import annotations

from django.test import SimpleTestCase

from apps.analysis.application.inference.integrity import build_integrity_block
from apps.analysis.application.inference.tasks.quality.predict import (
    LOW_CONFIDENCE_MARGIN,
    predict_quality_detailed,
)

DIM = 384


class _Encoder:
    def encode(self, texts, **kwargs):
        import numpy as np

        return np.asarray([[1.0] + [0.0] * (DIM - 1) for _ in texts], dtype=np.float32)


class _Head:
    """Level head whose top-two gap is whatever the case needs."""

    classes_ = ["fair", "good", "poor"]

    def __init__(self, margin: float) -> None:
        top = (1.0 + margin) / 2.0
        self._row = [1.0 - top, top, 0.0]

    def predict_proba(self, matrix):
        import numpy as np

        return np.asarray([self._row for _ in range(matrix.shape[0])], dtype=np.float64)


def _bundle(margin: float) -> dict:
    return {
        "heads": {"level": _Head(margin)},
        "_metadata": {
            "embedding_dim": DIM * 5,
            "include_document": True,
            "quality_level_to_score": {"poor": 30, "fair": 55, "good": 78},
        },
    }


def _resume() -> dict:
    return {
        "data": {
            "summary": "Analista com quatro anos em modelagem.",
            "skills": [{"name": "SQL"}],
            "experiences": [
                {"position": "Analista", "description": ["Cortei o fechamento em 40%."]}
            ],
            "educations": [{"course": "Estatistica", "degree": "Bacharelado"}],
        }
    }


def _score(margin: float, **kwargs):
    return predict_quality_detailed(
        "texto do curriculo",
        "pt-BR",
        None,
        probe_bundle=_bundle(margin),
        embeddings_model=_Encoder(),
        resume_data=_resume(),
        **kwargs,
    )


class MarginDecidesConfidenceTest(SimpleTestCase):
    def test_a_wide_margin_is_high_confidence(self):
        _s, _f, detail = _score(LOW_CONFIDENCE_MARGIN + 0.2)
        self.assertEqual(detail["confidence"], "high")
        self.assertEqual(detail["provider"], "quality_probe")

    def test_a_narrow_margin_is_low_confidence(self):
        _s, _f, detail = _score(LOW_CONFIDENCE_MARGIN - 0.05)
        self.assertEqual(detail["confidence"], "low")

    def test_low_confidence_still_publishes_a_score(self):
        score, _f, detail = _score(LOW_CONFIDENCE_MARGIN - 0.05)
        self.assertIsNotNone(score, "abstention marks the answer, it does not withhold it")
        self.assertEqual(detail["provider"], "quality_probe")

    def test_the_margin_is_reported_so_the_threshold_is_auditable(self):
        _s, _f, detail = _score(0.42)
        self.assertAlmostEqual(detail["margin"], 0.42, places=6)


class IntegrityKeepsTheTwoClaimsApartTest(SimpleTestCase):
    def test_low_confidence_is_not_degraded(self):
        block = build_integrity_block({"quality": "quality_probe"}, low_confidence_tasks=["quality"])
        self.assertFalse(block["degraded"], "a model answered; low confidence is not a rule answering")
        self.assertEqual(block["degradedTasks"], [])
        self.assertEqual(block["lowConfidenceTasks"], ["quality"])

    def test_the_field_is_always_present(self):
        block = build_integrity_block({"quality": "quality_probe"})
        self.assertEqual(block["lowConfidenceTasks"], [])


class RefusalNamesTheRealCauseTest(SimpleTestCase):
    """
    A resume gated off by completeness must not be reported as a missing artefact. That message sent
    an operator hunting for a bundle that was present and correct.
    """

    def test_completeness_gate_refusal_does_not_blame_the_bundle(self):
        score, _f, detail = _score(0.5, neural_allowed=False, allow_heuristic_answer=False)
        self.assertIsNone(score)
        reason = detail["reason"]
        self.assertIn("too incomplete", reason)
        self.assertIn("not a missing bundle", reason)

    def test_a_genuinely_absent_probe_still_reports_as_such(self):
        score, _f, detail = predict_quality_detailed(
            "texto",
            "pt-BR",
            None,
            probe_bundle=None,
            embeddings_model=None,
            resume_data=_resume(),
            allow_heuristic_answer=False,
        )
        self.assertIsNone(score)
        self.assertIn("unavailable", detail["reason"])
