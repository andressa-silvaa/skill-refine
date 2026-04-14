"""Deterministic split by resume_key (no leakage)."""
from __future__ import annotations

from django.test import SimpleTestCase

from apps.analysis.application.dataset_resume_split import assign_split_labels, split_rows


class TestAssignSplitLabels(SimpleTestCase):
    def test_same_seed_same_assignment(self):
        keys = [f"k{i}" for i in range(20)]
        a = assign_split_labels(keys, seed=42, train_ratio=0.7, val_ratio=0.15)
        b = assign_split_labels(keys, seed=42, train_ratio=0.7, val_ratio=0.15)
        self.assertEqual(a, b)

    def test_each_key_single_split(self):
        keys = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        m = assign_split_labels(keys, seed=1, train_ratio=0.7, val_ratio=0.15)
        self.assertEqual(set(m.keys()), set(keys))
        for v in m.values():
            self.assertIn(v, ("train", "val", "test"))


class TestSplitRows(SimpleTestCase):
    def test_same_resume_key_stays_in_one_split(self):
        rows = [
            {"resume_key": "rk1", "labels": {"seniority_label": "junior"}},
            {"resume_key": "rk1", "labels": {"seniority_label": "junior"}},
            {"resume_key": "rk2", "labels": {"seniority_label": "mid"}},
        ]
        splits, _, version = split_rows(rows, seed=0, train_ratio=0.5, val_ratio=0.25)
        self.assertTrue(version)
        per_resume: dict[str, set[str]] = {}
        for split_name, lst in splits.items():
            for row in lst:
                rk = row["resume_key"]
                per_resume.setdefault(rk, set()).add(split_name)
        for rk, names in per_resume.items():
            self.assertEqual(len(names), 1, msg=f"resume_key {rk} leaked across splits: {names}")
