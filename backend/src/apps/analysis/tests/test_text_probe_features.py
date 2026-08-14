"""
Feature width must not depend on how much of the resume happens to be filled in.

Training encodes the whole corpus in one call, so an empty section became a zero vector of full
width. Inference encodes one resume, and the empty-input branch used to return width 0 — the
concatenation came out 1536 instead of 1920 and the loader's interlock refused the row. It surfaced
as ``quality has no model answer``, pointing the operator at a bundle that was fine.

10.3% of the v3 corpus has at least one empty section, and 134 of those 160 are a missing summary,
which is ordinary in a real resume.
"""
from __future__ import annotations

from django.test import SimpleTestCase

from apps.analysis.application.inference.text_probe import (
    SECTION_ORDER,
    build_feature_row,
    embed_documents,
)

DIM = 384


class _Encoder:
    """Width-correct stub: one unit vector per text, whatever the text is."""

    def encode(self, texts, **kwargs):
        import numpy as np

        return np.asarray([[1.0] + [0.0] * (DIM - 1) for _ in texts], dtype=np.float32)


def _resume(**overrides) -> dict:
    data = {
        "targetPosition": "Analista de Dados",
        "summary": "Analista com quatro anos em modelagem e pipelines.",
        "skills": [{"name": "SQL"}],
        "experiences": [
            {
                "position": "Analista",
                "company": "A",
                "startDate": "2021-01",
                "isCurrent": True,
                "description": ["Construi pipelines que cortaram o fechamento em 40%."],
            }
        ],
        "educations": [{"institution": "UF", "course": "Estatistica", "degree": "Bacharelado"}],
    }
    data.update(overrides)
    return {"data": data}


class EmptyTextKeepsFullWidthTest(SimpleTestCase):
    def test_all_empty_input_still_returns_the_encoder_width(self):
        matrix = embed_documents(_Encoder(), ["", "   "])
        self.assertEqual(matrix.shape, (2, DIM))
        self.assertTrue((matrix == 0).all(), "an empty text must encode as zeros, as in training")

    def test_a_batch_mixing_empty_and_filled_keeps_one_width(self):
        matrix = embed_documents(_Encoder(), ["", "texto real"])
        self.assertEqual(matrix.shape, (2, DIM))
        self.assertTrue((matrix[0] == 0).all())
        self.assertFalse((matrix[1] == 0).all())


class FeatureRowWidthIsIndependentOfWhatIsFilledInTest(SimpleTestCase):
    EXPECTED = (len(SECTION_ORDER) + 1) * DIM

    def _width(self, resume: dict) -> int:
        return int(build_feature_row(_Encoder(), resume, "documento", include_document=True).shape[1])

    def test_a_complete_resume_has_the_bundle_width(self):
        self.assertEqual(self._width(_resume()), self.EXPECTED)

    def test_a_resume_with_no_summary_has_the_same_width(self):
        self.assertEqual(self._width(_resume(summary="")), self.EXPECTED)

    def test_a_resume_with_no_education_or_skills_has_the_same_width(self):
        self.assertEqual(self._width(_resume(educations=[], skills=[])), self.EXPECTED)

    def test_a_resume_with_no_experience_has_the_same_width(self):
        self.assertEqual(self._width(_resume(experiences=[])), self.EXPECTED)

    def test_an_almost_empty_resume_has_the_same_width(self):
        self.assertEqual(
            self._width({"data": {"summary": "", "experiences": [], "skills": [], "educations": []}}),
            self.EXPECTED,
        )
