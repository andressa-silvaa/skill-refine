"""ESCO retrieval for domain inference: ISCO mapping, label variants, cascade order."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from apps.analysis.application.inference.orchestrator import _domain_block
from apps.analysis.application.inference.tasks.target_fit.domain_inference import (
    DOMAIN_CATEGORIES,
    infer_domain_category,
)
from apps.analysis.application.inference.tasks.target_fit.esco_retrieval import (
    _label_variants,
    build_occupation_query,
    clear_esco_cache,
    lang_key,
    load_occupations,
)
from apps.analysis.application.inference.tasks.target_fit.isco_domains import (
    _ISCO_PREFIX_DOMAIN,
    domain_for_isco,
    isco_code_digits,
)

_OCCUPATIONS = [
    {
        "uri": "esco/nurse",
        "isco": "2221.1",
        "isco_group": "Nursing professionals",
        "labels": {"en": "registered nurse", "pt": "Enfermeiro/Enfermeira", "es": "enfermero/enfermera"},
        "alt": {"en": ["clinical nurse"], "pt": ["Enfermeira"], "es": []},
    },
    {
        "uri": "esco/developer",
        "isco": "2512.1",
        "isco_group": "Software developers",
        "labels": {"en": "software developer", "pt": "Desenvolvedor de software", "es": "desarrollador"},
        "alt": {"en": ["application programmer"], "pt": [], "es": []},
    },
]


class _StubEncoder:
    """Deterministic 3-d encoder: axis 0 is nursing, axis 1 is software, axis 2 is neither."""

    KEYS = ("nurse", "enferm", "developer", "desenvolvedor", "software")
    AXIS = {"nurse": 0, "enferm": 0, "developer": 1, "desenvolvedor": 1, "software": 1}

    def encode(self, texts, **kwargs):
        import numpy as np

        rows = []
        for text in texts:
            low = str(text).lower()
            vec = [0.0, 0.0, 0.0]
            for key in self.KEYS:
                if key in low:
                    vec[self.AXIS[key]] = 1.0
            if vec[0] == 0.0 and vec[1] == 0.0:
                vec[2] = 1.0
            rows.append(vec)
        matrix = np.asarray(rows, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / np.where(norms == 0.0, 1.0, norms)


class IscoDomainsTest(unittest.TestCase):
    def test_all_targets_are_public_categories(self):
        for prefix, domain in _ISCO_PREFIX_DOMAIN.items():
            self.assertIn(domain, DOMAIN_CATEGORIES, f"prefix {prefix}")

    def test_longest_prefix_wins(self):
        self.assertEqual(domain_for_isco("2166.1"), "creative")
        self.assertEqual(domain_for_isco("2165.4.1"), "engineering")
        self.assertEqual(domain_for_isco("1211.2"), "finance")
        self.assertEqual(domain_for_isco("1219"), "administrative")

    def test_sub_major_group_carries_the_field(self):
        self.assertEqual(domain_for_isco("2221.1"), "health")
        self.assertEqual(domain_for_isco("2330"), "education")
        self.assertEqual(domain_for_isco("2512.4"), "technology")
        self.assertEqual(domain_for_isco("2611"), "legal")
        self.assertEqual(domain_for_isco("8121.4"), "operations")

    def test_unknown_and_empty_are_general(self):
        self.assertEqual(domain_for_isco(""), "general")
        self.assertEqual(domain_for_isco("9799"), "general")
        self.assertEqual(domain_for_isco("not-a-code"), "general")

    def test_code_digits_stops_at_first_dot(self):
        self.assertEqual(isco_code_digits("2165.4.1"), "2165")
        self.assertEqual(isco_code_digits(" 331.2 "), "331")


class LabelVariantsTest(unittest.TestCase):
    def test_gender_variants_split_on_slash(self):
        variants = _label_variants(_OCCUPATIONS[0], "pt", 4)
        self.assertEqual(variants[0], "Enfermeiro")
        self.assertNotIn("Enfermeiro/Enfermeira", variants)

    def test_alt_labels_are_capped_and_deduped(self):
        row = {
            "labels": {"en": "nurse"},
            "alt": {"en": ["nurse", "Nurse", "clinical nurse", "ward nurse", "staff nurse", "night nurse"]},
        }
        variants = _label_variants(row, "en", 2)
        self.assertEqual(variants[:1], ["nurse"])
        self.assertLessEqual(len(variants), 3)
        self.assertEqual(len(variants), len({v.casefold() for v in variants}))

    def test_missing_language_falls_back_to_english(self):
        row = {"labels": {"en": "welder"}, "alt": {}}
        self.assertEqual(_label_variants(row, "pt", 4), ["welder"])

    def test_lang_key_normalizes_locales(self):
        self.assertEqual(lang_key("pt-BR"), "pt")
        self.assertEqual(lang_key("es-ES"), "es")
        self.assertEqual(lang_key("en-US"), "en")
        self.assertEqual(lang_key(""), "en")
        self.assertEqual(lang_key("de-DE"), "en")


class EscoCascadeTest(unittest.TestCase):
    def setUp(self):
        clear_esco_cache()
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.occupations_path = root / "esco.jsonl"
        self.occupations_path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in _OCCUPATIONS),
            encoding="utf-8",
        )
        self.options = {
            "occupations_path": str(self.occupations_path),
            "cache_dir": str(root / "cache"),
            "model_name": "stub-encoder",
            "top_k": 2,
        }

    def tearDown(self):
        clear_esco_cache()
        self._tmp.cleanup()

    def test_retrieval_wins_over_keywords(self):
        found = infer_domain_category(
            "Registered nurse at a large hospital",
            "en-US",
            embeddings_model=_StubEncoder(),
            esco_options=self.options,
        )
        self.assertEqual(found["provider"], "domain_embeddings")
        self.assertEqual(found["domainCategory"], "health")
        self.assertEqual(found["occupation"]["isco"], "2221.1")
        self.assertEqual(found["occupation"]["iscoGroup"], "Nursing professionals")
        self.assertGreater(found["occupation"]["cosine"], 0.5)
        self.assertTrue(found["evidenceTokens"])

    def test_occupation_query_overrides_text(self):
        found = infer_domain_category(
            "Enfermeiro com dez anos de hospital",
            "pt-BR",
            embeddings_model=_StubEncoder(),
            occupation_query="Desenvolvedor de software",
            esco_options=self.options,
        )
        self.assertEqual(found["domainCategory"], "technology")
        self.assertEqual(found["evidenceTokens"][0], "Desenvolvedor de software")

    def test_far_query_falls_back_to_keywords(self):
        found = infer_domain_category(
            "Advogado tributarista com atuação em tribunal",
            "pt-BR",
            embeddings_model=_StubEncoder(),
            esco_options=self.options,
        )
        self.assertEqual(found["provider"], "domain_keywords")
        self.assertEqual(found["domainCategory"], "legal")

    def test_broken_model_falls_back_to_keywords(self):
        class _Boom:
            def encode(self, texts, **kwargs):
                raise RuntimeError("no model")

        found = infer_domain_category(
            "Enfermeiro hospitalar",
            "pt-BR",
            embeddings_model=_Boom(),
            esco_options=self.options,
        )
        self.assertEqual(found["provider"], "domain_keywords")
        self.assertEqual(found["domainCategory"], "health")

    def test_missing_taxonomy_file_falls_back_to_keywords(self):
        found = infer_domain_category(
            "Enfermeiro hospitalar",
            "pt-BR",
            embeddings_model=_StubEncoder(),
            esco_options={**self.options, "occupations_path": str(self.occupations_path) + ".missing"},
        )
        self.assertEqual(found["provider"], "domain_keywords")
        self.assertEqual(found["domainCategory"], "health")

    def test_index_is_cached_after_first_call(self):
        model = _StubEncoder()
        calls: list[int] = []
        original = model.encode

        def counting(texts, **kwargs):
            calls.append(len(texts))
            return original(texts, **kwargs)

        model.encode = counting
        for _ in range(3):
            infer_domain_category(
                "software developer",
                "en-US",
                embeddings_model=model,
                esco_options=self.options,
            )
        self.assertEqual(sum(1 for n in calls if n > 1), 1, f"labels re-embedded: {calls}")


class KeywordPathContractTest(unittest.TestCase):
    def test_no_model_keeps_legacy_shape(self):
        found = infer_domain_category("Enfermeiro hospitalar", "pt-BR")
        self.assertEqual(found["provider"], "domain_keywords")
        self.assertEqual(found["domainCategory"], "health")
        self.assertNotIn("occupation", found)

    def test_domain_block_adds_nothing_on_keyword_path(self):
        block = _domain_block(infer_domain_category("Enfermeiro hospitalar", "pt-BR"))
        self.assertEqual(set(block), {"category", "confidence", "evidenceTokens"})

    def test_domain_block_exposes_esco_fields(self):
        block = _domain_block(
            {
                "domainCategory": "health",
                "confidence": "high",
                "evidenceTokens": ["registered nurse"],
                "provider": "domain_embeddings",
                "occupation": {
                    "uri": "esco/nurse",
                    "label": "registered nurse",
                    "isco": "2221.1",
                    "iscoGroup": "Nursing professionals",
                    "cosine": 0.71,
                },
                "domainMargin": 0.2,
                "occupationGap": 0.1,
            }
        )
        self.assertEqual(block["provider"], "domain_embeddings")
        self.assertEqual(block["escoOccupation"]["isco"], "2221.1")
        self.assertEqual(block["domainMargin"], 0.2)


class OccupationQueryTest(unittest.TestCase):
    def test_query_is_titles_skills_and_courses(self):
        query = build_occupation_query(
            {
                "data": {
                    "targetPosition": "Enfermeiro Chefe",
                    "experiences": [
                        {"position": "Enfermeiro", "description": ["Atendi 40 pacientes por turno"]},
                        {"position": "Técnico de Enfermagem", "description": []},
                    ],
                    "skills": [{"name": "UTI"}, {"name": "Triagem"}],
                    "educations": [{"course": "Enfermagem"}],
                }
            }
        )
        self.assertIn("Enfermeiro Chefe", query)
        self.assertIn("Técnico de Enfermagem", query)
        self.assertIn("UTI, Triagem", query)
        self.assertIn("Enfermagem", query)
        self.assertNotIn("pacientes por turno", query)

    def test_empty_resume_gives_empty_query(self):
        self.assertEqual(build_occupation_query({}), "")


class RealTaxonomyTest(unittest.TestCase):
    def test_shipped_taxonomy_loads_with_domains(self):
        clear_esco_cache()
        rows = load_occupations()
        if not rows:
            self.skipTest("ml/data/reference/esco_occupations.jsonl not available")
        self.assertGreater(len(rows), 1000)
        for row in rows:
            self.assertIn(row["domain"], DOMAIN_CATEGORIES)
        general = sum(1 for row in rows if row["domain"] == "general")
        self.assertLess(general / len(rows), 0.05, "too many occupations left unmapped")
        clear_esco_cache()
