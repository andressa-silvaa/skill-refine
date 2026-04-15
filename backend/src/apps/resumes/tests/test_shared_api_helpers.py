from __future__ import annotations

import uuid
from unittest.mock import Mock

from django.test import SimpleTestCase
from rest_framework import status

from shared.api.pagination import (
    parse_history_limit_offset,
    parse_limit_offset,
    parse_notifications_list_pagination,
)
from shared.api.request_user import require_authenticated_user_id


class TestRequireAuthenticatedUserId(SimpleTestCase):
    def test_anonymous_returns_401_contract(self):
        class UnauthenticatedUser:
            id = None

        req = Mock()
        req.user = UnauthenticatedUser()
        uid, err = require_authenticated_user_id(req)
        self.assertIsNone(uid)
        self.assertIsNotNone(err)
        self.assertEqual(err.status_code, status.HTTP_401_UNAUTHORIZED)
        body = err.data
        self.assertEqual(body.get("message"), "Não autenticado.")
        self.assertEqual((body.get("error") or {}).get("code"), "unauthorized")

    def test_authenticated_returns_str_uuid(self):
        req = Mock()
        pk = uuid.uuid4()
        req.user = Mock(id=pk)
        uid, err = require_authenticated_user_id(req)
        self.assertIsNone(err)
        self.assertEqual(uid, str(pk))


class TestParseLimitOffsetStrict(SimpleTestCase):
    def test_invalid_limit_string_returns_400(self):
        _, err = parse_limit_offset(
            limit_param="abc",
            offset_param="0",
            limit_default=20,
            offset_default=0,
            limit_min=1,
            limit_max=100,
        )
        self.assertIsNotNone(err)
        self.assertEqual(err.status_code, status.HTTP_400_BAD_REQUEST)


class TestParseHistoryLimitOffset(SimpleTestCase):
    """Matches analysis history endpoint: invalid ints fall back to defaults before range check."""

    def test_non_numeric_limit_uses_default(self):
        out, err = parse_history_limit_offset(
            limit_param="abc",
            offset_param=0,
            limit_default=20,
            offset_default=0,
            limit_max=100,
        )
        self.assertIsNone(err)
        self.assertEqual(out, (20, 0))

    def test_limit_out_of_range_returns_400(self):
        _, err = parse_history_limit_offset(
            limit_param=150,
            offset_param=0,
            limit_default=20,
            offset_default=0,
            limit_max=100,
        )
        self.assertIsNotNone(err)
        self.assertEqual(err.status_code, status.HTTP_400_BAD_REQUEST)


class TestParseNotificationsListPagination(SimpleTestCase):
    def test_invalid_limit_returns_400(self):
        _, err = parse_notifications_list_pagination(limit_param="abc", offset_param="0")
        self.assertIsNotNone(err)
        self.assertEqual(err.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_offset_clamps_to_zero(self):
        out, err = parse_notifications_list_pagination(limit_param="10", offset_param="-5")
        self.assertIsNone(err)
        self.assertEqual(out, (10, 0))

    def test_defaults_when_params_missing(self):
        out, err = parse_notifications_list_pagination(limit_param=None, offset_param=None)
        self.assertIsNone(err)
        self.assertEqual(out, (20, 0))
