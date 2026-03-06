from __future__ import annotations

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.infrastructure.models import User
from apps.resumes.infrastructure.models import Resume, ResumeStatus, ResumeVersion


class VersionListPaginationApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, _ = User.objects.get_or_create(
            email="version-pagination@test.local",
            defaults={"full_name": "Version Pagination", "status": "active"},
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/resumes/api/versions"
        self.resume = Resume.objects.create(
            user_id=self.user.id,
            name="Versioned",
            status=ResumeStatus.DRAFT,
            target_position="Dev",
        )
        for idx in range(3):
            ResumeVersion.objects.create(
                resume_id=self.resume.id,
                user_id=self.user.id,
                version_number=idx + 1,
                is_current=idx == 2,
                snapshot_json={"v": idx + 1},
                change_summary_json=["x"],
            )

    def test_versions_without_limit_offset_keeps_legacy_shape(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("items", data)
        self.assertNotIn("limit", data)
        self.assertEqual(len(data["items"]), 3)

    def test_versions_with_pagination_returns_metadata(self):
        resp = self.client.get(self.url, {"limit": "2", "offset": "0"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["limit"], 2)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(data["total"], 3)
        self.assertTrue(data["has_next"])
        self.assertEqual(data["next_offset"], 2)

    def test_versions_invalid_limit_returns_400(self):
        cases = [
            {"limit": "0", "offset": "0"},
            {"limit": "101", "offset": "0"},
            {"limit": "abc", "offset": "0"},
        ]
        for query in cases:
            with self.subTest(query=query):
                resp = self.client.get(self.url, query)
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_versions_invalid_offset_returns_400(self):
        cases = [
            {"limit": "2", "offset": "-1"},
            {"limit": "2", "offset": "abc"},
            {"offset": "-1"},
        ]
        for query in cases:
            with self.subTest(query=query):
                resp = self.client.get(self.url, query)
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

