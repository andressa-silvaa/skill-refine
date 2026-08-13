"""
Ordering the improvement list by measured gain instead of by the order the branches run in.

The table under test is real (``ml/models/insight_gain_v1``), but these cases pin the *rules*, not
the current numbers: that a measured suggestion outranks an unmeasured one, that an unmeasured one
keeps the priority its branch declared, and that a suggestion whose measured gain is negative is
demoted no matter how confidently the branch labelled it. The numbers move whenever the corpus grows;
the rules should not.
"""
from __future__ import annotations

from django.test import SimpleTestCase

from apps.analysis.application.inference.postprocess.insight_ranking import (
    FALLBACK_PROVIDER,
    PROVIDER,
    rank_improvements,
)

GAINS = {
    "a.big": {"within_band_gain": 2.90, "pooled_gain": 14.58},
    "a.medium": {"within_band_gain": 1.73, "pooled_gain": 8.66},
    "a.flat": {"within_band_gain": 0.33, "pooled_gain": 0.29},
    "a.slightly_negative": {"within_band_gain": -0.08, "pooled_gain": -0.46},
    "a.negative": {"within_band_gain": -0.80, "pooled_gain": -3.24},
}
META = {"task": "insight_gain", "gains": GAINS}


def _items(*keys_and_priorities: tuple[str, str]) -> list[dict]:
    return [{"key": key, "priority": priority} for key, priority in keys_and_priorities]


class RankingRulesTest(SimpleTestCase):
    def test_measured_items_sort_by_gain_regardless_of_input_order(self):
        items = _items(("a.negative", "high"), ("a.big", "low"), ("a.medium", "medium"))
        ordered, provider = rank_improvements(items, META)
        self.assertEqual(provider, PROVIDER)
        self.assertEqual([i["key"] for i in ordered], ["a.big", "a.medium", "a.negative"])

    def test_a_negative_gain_is_demoted_however_the_branch_labelled_it(self):
        ordered, _provider = rank_improvements(_items(("a.negative", "high")), META)
        self.assertEqual(ordered[0]["priority"], "low")

    def test_unmeasured_items_keep_their_declared_priority_and_sort_last(self):
        items = _items(("a.unmeasured", "high"), ("a.negative", "high"))
        ordered, _provider = rank_improvements(items, META)
        self.assertEqual([i["key"] for i in ordered], ["a.negative", "a.unmeasured"])
        self.assertEqual(ordered[1]["priority"], "high")

    def test_unmeasured_items_keep_their_relative_order(self):
        items = _items(("a.x", "medium"), ("a.y", "medium"), ("a.z", "medium"))
        ordered, _provider = rank_improvements(items, META)
        self.assertEqual([i["key"] for i in ordered], ["a.x", "a.y", "a.z"])

    def test_rank_is_published_as_evidence_not_as_a_score(self):
        ordered, _provider = rank_improvements(_items(("a.big", "low")), META)
        evidence = ordered[0]["evidence"]
        self.assertEqual(evidence["expectedGainRank"], 1)
        self.assertNotIn("gain", evidence)
        self.assertNotIn("expectedGain", evidence)

    def test_input_is_not_mutated(self):
        items = _items(("a.negative", "high"))
        rank_improvements(items, META)
        self.assertEqual(items[0]["priority"], "high")


class RankingFallbackTest(SimpleTestCase):
    """Without a table the list must come back exactly as the branches built it."""

    def test_no_table_leaves_order_and_priorities_untouched(self):
        items = _items(("a.negative", "high"), ("a.big", "low"))
        ordered, provider = rank_improvements(items, None)
        self.assertEqual(provider, FALLBACK_PROVIDER)
        self.assertEqual([i["key"] for i in ordered], ["a.negative", "a.big"])
        self.assertEqual(ordered[0]["priority"], "high")

    def test_a_table_with_no_usable_gains_falls_back(self):
        empty = {"task": "insight_gain", "gains": {"a.big": {"within_band_gain": None}}}
        ordered, provider = rank_improvements(_items(("a.big", "high")), empty)
        self.assertEqual(provider, FALLBACK_PROVIDER)
        self.assertEqual(ordered[0]["priority"], "high")

    def test_empty_input_is_returned_as_is(self):
        ordered, provider = rank_improvements([], META)
        self.assertEqual(ordered, [])
        self.assertEqual(provider, FALLBACK_PROVIDER)


class ShippedTableTest(SimpleTestCase):
    """
    The artefact under ml/models must load and must still rank the two bullet-driven suggestions
    above the education one, which measures a negative gain. A missing table fails loudly here rather
    than silently restoring the hand-written order in production.
    """

    def setUp(self):
        from django.conf import settings

        from apps.analysis.application.inference.config import get_config
        from apps.analysis.application.inference.postprocess.insight_ranking import (
            clear_gain_cache,
            load_gain_table,
        )

        clear_gain_cache()
        config = dict(get_config(settings))
        config["insight_ranking_enabled"] = True
        self.meta = load_gain_table(config)
        if self.meta is None:
            self.fail("insight_gain_v1 table missing; insights would silently keep the guessed order")

    def test_metrics_and_verbs_outrank_the_education_gap(self):
        keys = [
            "analysis.insights.improvements.education_target_gap",
            "analysis.insights.improvements.add_metrics",
            "analysis.insights.improvements.use_action_verbs",
        ]
        ordered, provider = rank_improvements(
            [{"key": k, "priority": "high"} for k in keys], self.meta
        )
        self.assertEqual(provider, PROVIDER)
        self.assertEqual(
            [i["key"].rsplit(".", 1)[-1] for i in ordered],
            ["add_metrics", "use_action_verbs", "education_target_gap"],
        )
        self.assertEqual(ordered[-1]["priority"], "low")

    def test_the_table_declares_itself_correlational(self):
        self.assertIs(self.meta.get("causal"), False)
