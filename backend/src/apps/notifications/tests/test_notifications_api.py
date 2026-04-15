"""Tests for notifications API: ownership, unread count, mark read."""
from __future__ import annotations

from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.infrastructure.models import User
from apps.notifications.models import Notification, NotificationType
from apps.notifications.services import create_notification


class NotificationsApiTestCase(TestCase):
    def test_unread_count_requires_auth(self):
        client = APIClient()
        res = client.get("/notifications/unread-count/")
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_unread_count_returns_zero_for_new_user(self):
        user, _ = User.objects.get_or_create(
            email="notif-test-u@example.com",
            defaults={"full_name": "User", "status": "active"},
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get("/notifications/unread-count/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["count"], 0)

    def test_unread_count_returns_correct_count(self):
        user, _ = User.objects.get_or_create(
            email="notif-test-count@example.com",
            defaults={"full_name": "User", "status": "active"},
        )
        create_notification(str(user.id), NotificationType.ANALYSIS_DONE, "notifications.analysisDone", {"name": "X"})
        create_notification(str(user.id), NotificationType.PDF_READY, "notifications.pdfReady", {"name": "Y"})
        n3 = create_notification(str(user.id), NotificationType.SYSTEM, "notifications.system", {})
        n3.is_read = True
        n3.save()
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get("/notifications/unread-count/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["count"], 2)

    def test_mark_read_requires_ownership(self):
        user1, _ = User.objects.get_or_create(
            email="notif-test-u1@x.com",
            defaults={"full_name": "U1", "status": "active"},
        )
        user2, _ = User.objects.get_or_create(
            email="notif-test-u2@x.com",
            defaults={"full_name": "U2", "status": "active"},
        )
        n = create_notification(str(user1.id), NotificationType.SYSTEM, "notifications.system", {})
        client = APIClient()
        client.force_authenticate(user=user2)
        res = client.post(f"/notifications/{n.id}/read/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_read_success(self):
        user, _ = User.objects.get_or_create(
            email="notif-test-mark@x.com",
            defaults={"full_name": "U", "status": "active"},
        )
        n = create_notification(str(user.id), NotificationType.SYSTEM, "notifications.system", {})
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.post(f"/notifications/{n.id}/read/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_mark_all_read(self):
        user, _ = User.objects.get_or_create(
            email="notif-test-all@x.com",
            defaults={"full_name": "U", "status": "active"},
        )
        create_notification(str(user.id), NotificationType.SYSTEM, "notifications.system", {})
        create_notification(str(user.id), NotificationType.PDF_READY, "notifications.pdfReady", {"name": "X"})
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.post("/notifications/read-all/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.filter(user_id=user.id, is_read=False).count(), 0)

    def test_list_invalid_limit_returns_400(self):
        user, _ = User.objects.get_or_create(
            email="notif-test-bad-limit@x.com",
            defaults={"full_name": "U", "status": "active"},
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get("/notifications/", {"limit": "not-a-number"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_negative_offset_clamps_to_zero(self):
        user, _ = User.objects.get_or_create(
            email="notif-test-neg-offset@x.com",
            defaults={"full_name": "U", "status": "active"},
        )
        create_notification(str(user.id), NotificationType.SYSTEM, "notifications.system", {})
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get("/notifications/", {"limit": "10", "offset": "-5"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        body = res.json()
        self.assertEqual(body["offset"], 0)
        self.assertEqual(body["limit"], 10)
