from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response

from shared.api.responses import error_response


def parse_limit_offset(
    *,
    limit_param: str | None,
    offset_param: str | None,
    limit_default: int,
    offset_default: int,
    limit_min: int,
    limit_max: int,
) -> tuple[tuple[int, int] | None, Response | None]:
    try:
        limit = int(limit_param) if limit_param not in (None, "") else limit_default
    except ValueError:
        limit = None
    try:
        offset = int(offset_param) if offset_param not in (None, "") else offset_default
    except ValueError:
        offset = -1

    if limit is None or limit < limit_min or limit > limit_max:
        return None, error_response(
            "validation_error",
            f"Parâmetro limit deve ser um número entre {limit_min} e {limit_max}.",
            status.HTTP_400_BAD_REQUEST,
        )
    if offset < 0:
        return None, error_response(
            "validation_error",
            "Parâmetro offset deve ser um número maior ou igual a 0.",
            status.HTTP_400_BAD_REQUEST,
        )

    return (limit, offset), None


def parse_history_limit_offset(
    *,
    limit_param: Any,
    offset_param: Any,
    limit_default: int,
    offset_default: int,
    limit_max: int,
) -> tuple[tuple[int, int] | None, Response | None]:
    try:
        limit = int(limit_param) if limit_param not in (None, "") else limit_default
    except (TypeError, ValueError):
        limit = limit_default
    try:
        offset = int(offset_param) if offset_param not in (None, "") else offset_default
    except (TypeError, ValueError):
        offset = offset_default

    if limit < 1 or limit > limit_max:
        return None, error_response(
            "validation_error",
            f"Parâmetro limit deve ser entre 1 e {limit_max}.",
            status.HTTP_400_BAD_REQUEST,
        )
    if offset < 0:
        return None, error_response(
            "validation_error",
            "Parâmetro offset deve ser maior ou igual a 0.",
            status.HTTP_400_BAD_REQUEST,
        )

    return (limit, offset), None


def parse_notifications_list_pagination(
    *,
    limit_param: str | None,
    offset_param: str | None,
) -> tuple[tuple[int, int] | None, Response | None]:
    try:
        limit_base = int(limit_param) if limit_param not in (None, "") else 20
    except (TypeError, ValueError):
        return None, error_response(
            "validation_error",
            "Parâmetro limit deve ser um número entre 1 e 100.",
            status.HTTP_400_BAD_REQUEST,
        )
    limit = min(max(limit_base, 1), 100)

    try:
        offset_base = int(offset_param) if offset_param not in (None, "") else 0
    except (TypeError, ValueError):
        return None, error_response(
            "validation_error",
            "Parâmetro offset deve ser um número maior ou igual a 0.",
            status.HTTP_400_BAD_REQUEST,
        )
    offset = max(offset_base, 0)

    return (limit, offset), None
