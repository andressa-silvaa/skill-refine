"""Permissions for internal analysis review endpoints (no Django admin user model)."""
from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasAnalysisInternalReviewSecret(BasePermission):
    """
    Require header ``X-Analysis-Internal-Token`` matching ``ANALYSIS_INTERNAL_REVIEW_SECRET``.

    - Secret unset → deny.
    - When ``DEBUG`` is False, secret shorter than ``ANALYSIS_INTERNAL_SECRET_MIN_LENGTH`` → deny
      (weak secrets are not accepted in production-like mode).
    """

    message = "Internal review authentication failed."

    def has_permission(self, request, view) -> bool:
        secret = (getattr(settings, "ANALYSIS_INTERNAL_REVIEW_SECRET", "") or "").strip()
        if not secret:
            return False

        min_len = int(getattr(settings, "ANALYSIS_INTERNAL_SECRET_MIN_LENGTH", 20))
        if not settings.DEBUG and len(secret) < min_len:
            return False

        token = (request.headers.get("X-Analysis-Internal-Token") or "").strip()
        return token == secret
