"""Compatibility model exports for Django app loading and legacy imports."""

from apps.audit.infrastructure.models import AuditLog

__all__ = ["AuditLog"]


