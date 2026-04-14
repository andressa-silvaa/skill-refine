"""
Centralized API error response helpers.
Contract: same payload shape and status codes as previous per-endpoint implementations.
"""
from __future__ import annotations

from typing import Any

from rest_framework.response import Response


def canonical_error_code(code: str) -> str:
    """Normalize error code to uppercase, stripped. Preserves API contract."""
    return (code or "").strip().upper()


def error_response(
    code: str,
    message: str,
    http_status: int,
    headers: dict[str, str] | None = None,
) -> Response:
    """Generic error response. Payload: error, error_code, message (contract-preserving)."""
    canonical = canonical_error_code(code)
    payload = {
        "error": {"code": code, "error_code": canonical, "message": message},
        "error_code": canonical,
        "message": message,
    }
    return Response(payload, status=http_status, headers=headers or {})


def field_error_response(
    code: str, message: str, fields: dict[str, str], http_status: int
) -> Response:
    """Validation/field error response. Payload: error, error_code, message, fields."""
    canonical = canonical_error_code(code)
    payload = {
        "error": {"code": code, "error_code": canonical, "message": message},
        "error_code": canonical,
        "message": message,
        "fields": fields,
    }
    return Response(payload, status=http_status)


def extract_error_message(value: Any) -> str:
    """Extract a single string message from serializer error value (list/dict/str)."""
    if value is None:
        return "Valor inválido."
    if isinstance(value, (list, tuple)):
        if not value:
            return "Valor inválido."
        return str(value[0])
    if isinstance(value, dict):
        if not value:
            return "Valor inválido."
        first = next(iter(value.values()))
        return extract_error_message(first)
    return str(value)


def serializer_field_errors(serializer: Any) -> dict[str, str]:
    """Build field name -> message dict from DRF serializer.errors (contract-preserving)."""
    fields: dict[str, str] = {}
    for key, val in serializer.errors.items():
        if not key:
            continue
        fields[key] = extract_error_message(val)
    return fields
