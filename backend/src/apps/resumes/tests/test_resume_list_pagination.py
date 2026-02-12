"""
Tests for GET /resumes pagination: compat (no params) and paginated (limit/offset).
Run: python manage.py test apps.resumes.tests.test_resume_list_pagination -v 2
"""
from __future__ import annotations

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.infrastructure.models import User
from apps.resumes.infrastructure.models import Resume, ResumeStatus


class ResumeListPaginationTest(TestCase):
    """GET /resumes: compat when no params, paginated when limit/offset present."""

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            email="pagination-test@test.local",
            defaults={"full_name": "Pagination User", "status": "active"},
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = "/resumes/api/resumes"

        # Ensure at least 3 resumes for pagination tests
        existing = list(
            Resume.objects.filter(user_id=self.user.id, deleted_at__isnull=True).order_by("-updated_at")
        )
        for i in range(max(0, 3 - len(existing))):
            Resume.objects.create(
                user_id=self.user.id,
                name=f"Resume pagination {i}",
                status=ResumeStatus.DRAFT,
                target_position="Dev",
            )

    def test_get_without_params_compat(self):
        """No limit/offset → same shape as before: only 'items' key (compat)."""
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("items", data)
        self.assertIsInstance(data["items"], list)
        # Must NOT include pagination metadata when no params (compat)
        self.assertNotIn("limit", data)
        self.assertNotIn("offset", data)
        self.assertNotIn("total", data)
        self.assertNotIn("has_next", data)
        self.assertNotIn("next_offset", data)

    def test_get_with_limit_offset_returns_metadata(self):
        """With limit and offset → items + limit, offset, total, has_next, next_offset."""
        resp = self.client.get(self.url, {"limit": "20", "offset": "0"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("items", data)
        self.assertEqual(data["limit"], 20)
        self.assertEqual(data["offset"], 0)
        self.assertIn("total", data)
        self.assertIsInstance(data["total"], int)
        self.assertIn("has_next", data)
        self.assertIsInstance(data["has_next"], bool)
        self.assertIn("next_offset", data)
        if data["has_next"]:
            self.assertEqual(data["next_offset"], 20)
        else:
            self.assertIsNone(data["next_offset"])

    def test_get_limit_1_returns_one_item(self):
        """limit=1 returns one item, total and has_next correct."""
        resp = self.client.get(self.url, {"limit": "1", "offset": "0"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["limit"], 1)
        self.assertEqual(data["offset"], 0)
        self.assertGreaterEqual(data["total"], 1)
        self.assertEqual(data["has_next"], data["total"] > 1)
        if data["total"] > 1:
            self.assertEqual(data["next_offset"], 1)

    def test_get_limit_invalid_returns_400(self):
        """limit=0, limit=101, limit=abc → 400 validation_error."""
        for query in [{"limit": "0"}, {"limit": "101"}, {"limit": "abc"}]:
            resp = self.client.get(self.url, query)
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
            data = resp.json()
            self.assertIn("error_code", data)
            self.assertIn("message", data)

    def test_get_offset_invalid_returns_400(self):
        """offset=-1 or offset=abc → 400."""
        for query in [{"offset": "-1"}, {"offset": "abc"}, {"limit": "10", "offset": "-1"}]:
            resp = self.client.get(self.url, query)
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
            data = resp.json()
            self.assertIn("error_code", data)

    def test_get_offset_beyond_total(self):
        """offset beyond total → items=[], has_next=False."""
        resp = self.client.get(self.url, {"limit": "10", "offset": "9999"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data["items"], [])
        self.assertEqual(data["limit"], 10)
        self.assertEqual(data["offset"], 9999)
        self.assertIsInstance(data["total"], int)
        self.assertFalse(data["has_next"])
        self.assertIsNone(data["next_offset"])

    def test_get_paginated_item_shape_unchanged(self):
        """Each item in items has same shape as list payload (id, name, updatedAt, status, score, tags, skills)."""
        resp = self.client.get(self.url, {"limit": "5", "offset": "0"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        for item in data["items"]:
            self.assertIn("id", item)
            self.assertIn("name", item)
            self.assertIn("updatedAt", item)
            self.assertIn("status", item)
            self.assertIn("score", item)
            self.assertIn("tags", item)
            self.assertIn("skills", item)

    def test_get_ordering_most_recent_first(self):
        """Items ordered by updated_at descending (most recent first)."""
        resp = self.client.get(self.url, {"limit": "10", "offset": "0"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        if len(data["items"]) < 2:
            return
        dates = [item["updatedAt"] for item in data["items"]]
        self.assertEqual(dates, sorted(dates, reverse=True))
