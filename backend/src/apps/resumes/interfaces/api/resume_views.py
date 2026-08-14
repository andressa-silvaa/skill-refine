"""Resume CRUD, list, duplicate, token, pdf-data views."""
from __future__ import annotations

from datetime import date

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.resumes.infrastructure.models import ResumeContact, ResumeStatus
from shared.api.responses import (
    error_response as _error,
    field_error_response as _field_error,
    serializer_field_errors as _serializer_field_errors,
)
from shared.auth.drf import request_meta

from .payloads import resume_detail_payload, resume_payload
from .serializers import ResumeDraftSerializer
from .services import (
    create_pdf_token,
    create_resume_draft,
    delete_resume_soft,
    duplicate_resume,
    get_resume_for_edit,
    get_resume_for_pdf_data,
    get_resume_by_id_and_user,
    list_resumes,
    list_resumes_paginated,
    parse_pdf_token,
    update_resume_draft,
    validate_complete,
)
from .version_services import maybe_create_version_after_save
from .view_helpers import (
    invalidate_dashboard_cache_for_user,
    parse_limit_offset,
    require_user_id,
)

from .resume_action_views import ResumeDuplicateView, ResumePdfDataView, ResumePdfTokenView


PAGINATION_LIMIT_MIN = 1
PAGINATION_LIMIT_MAX = 100
PAGINATION_LIMIT_DEFAULT = 20
PAGINATION_OFFSET_DEFAULT = 0
LIST_SORT_ALLOWED = {"recent", "oldest", "score", "name"}


def _parse_date_or_none(raw: str | None):
    if raw in (None, ""):
        return None
    try:
        return date.fromisoformat(str(raw).strip())
    except ValueError:
        return "invalid"


def _parse_list_filters(request):
    status_value = (request.query_params.get("status") or "").strip()
    search = (request.query_params.get("search") or "").strip()
    score_min_raw = (request.query_params.get("score_min") or "").strip()
    score_max_raw = (request.query_params.get("score_max") or "").strip()
    include_no_score_raw = (request.query_params.get("include_no_score") or "").strip().lower()
    updated_from_raw = (request.query_params.get("updated_from") or "").strip()
    updated_to_raw = (request.query_params.get("updated_to") or "").strip()
    sort = (request.query_params.get("sort") or "recent").strip() or "recent"

    allowed_statuses = {value for value, _ in ResumeStatus.choices}
    if status_value and status_value not in allowed_statuses:
        return (None, _error("validation_error", "Parâmetro status inválido.", status.HTTP_400_BAD_REQUEST))

    score_min = None
    score_max = None
    if score_min_raw:
        try:
            score_min = int(score_min_raw)
        except ValueError:
            return (None, _error("validation_error", "Parâmetro score_min inválido.", status.HTTP_400_BAD_REQUEST))
    if score_max_raw:
        try:
            score_max = int(score_max_raw)
        except ValueError:
            return (None, _error("validation_error", "Parâmetro score_max inválido.", status.HTTP_400_BAD_REQUEST))
    if score_min is not None and (score_min < 0 or score_min > 100):
        return (None, _error("validation_error", "Parâmetro score_min deve ser entre 0 e 100.", status.HTTP_400_BAD_REQUEST))
    if score_max is not None and (score_max < 0 or score_max > 100):
        return (None, _error("validation_error", "Parâmetro score_max deve ser entre 0 e 100.", status.HTTP_400_BAD_REQUEST))
    if score_min is not None and score_max is not None and score_min > score_max:
        return (None, _error("validation_error", "Parâmetro score_min não pode ser maior que score_max.", status.HTTP_400_BAD_REQUEST))

    updated_from = _parse_date_or_none(updated_from_raw)
    updated_to = _parse_date_or_none(updated_to_raw)
    if updated_from == "invalid":
        return (None, _error("validation_error", "Parâmetro updated_from inválido (use YYYY-MM-DD).", status.HTTP_400_BAD_REQUEST))
    if updated_to == "invalid":
        return (None, _error("validation_error", "Parâmetro updated_to inválido (use YYYY-MM-DD).", status.HTTP_400_BAD_REQUEST))
    if updated_from and updated_to and updated_from > updated_to:
        return (None, _error("validation_error", "Parâmetro updated_from não pode ser maior que updated_to.", status.HTTP_400_BAD_REQUEST))

    if sort not in LIST_SORT_ALLOWED:
        return (
            None,
            _error(
                "validation_error",
                f"Parâmetro sort inválido. Valores permitidos: {', '.join(sorted(LIST_SORT_ALLOWED))}.",
                status.HTTP_400_BAD_REQUEST,
            ),
        )

    include_no_score = include_no_score_raw in ("1", "true", "yes")
    return (
        {
            "status": status_value or None,
            "search": search or None,
            "score_min": score_min,
            "score_max": score_max,
            "include_no_score": include_no_score,
            "updated_from": updated_from,
            "updated_to": updated_to,
            "sort": sort,
        },
        None,
    )


class ResumeListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response

        filters, filters_error_response = _parse_list_filters(request)
        if filters_error_response is not None:
            return filters_error_response

        limit_param = request.query_params.get("limit")
        offset_param = request.query_params.get("offset")

        if limit_param is None and offset_param is None:
            items = list_resumes(user_id, filters=filters)
            return Response({"items": [resume_payload(r) for r in items]}, status=status.HTTP_200_OK)

        page_params, page_error = parse_limit_offset(
            limit_param=limit_param,
            offset_param=offset_param,
            limit_default=PAGINATION_LIMIT_DEFAULT,
            offset_default=PAGINATION_OFFSET_DEFAULT,
            limit_min=PAGINATION_LIMIT_MIN,
            limit_max=PAGINATION_LIMIT_MAX,
        )
        if page_error:
            return page_error
        limit, offset = page_params

        page, total = list_resumes_paginated(user_id, limit, offset, filters=filters)
        next_offset = offset + limit
        has_next = next_offset < total

        payload = {
            "items": [resume_payload(r) for r in page],
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_next": has_next,
            "next_offset": next_offset if has_next else None,
        }
        return Response(payload, status=status.HTTP_200_OK)

    def post(self, request):
        ser = ResumeDraftSerializer(data=request.data)
        if not ser.is_valid():
            fields = _serializer_field_errors(ser)
            return _field_error("validation_error", "Dados inválidos.", fields, status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        status_value = data.get("status") or "draft"
        if status_value == "complete":
            fields = validate_complete(data)
            if fields:
                return _field_error("validation_error", "Dados inválidos.", fields, status.HTTP_400_BAD_REQUEST)

        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response

        _ = request_meta(request)

        resume = create_resume_draft(user_id, data)
        maybe_create_version_after_save(user_id, str(resume.id))
        invalidate_dashboard_cache_for_user(user_id)
        return Response(resume_payload(resume), status=status.HTTP_201_CREATED)


class ResumeDraftUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_id):
        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response

        resume = get_resume_for_edit(user_id, resume_id)
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        return Response(resume_detail_payload(resume), status=status.HTTP_200_OK)

    def patch(self, request, resume_id):
        ser = ResumeDraftSerializer(data=request.data, partial=True)
        if not ser.is_valid():
            fields = _serializer_field_errors(ser)
            return _field_error("validation_error", "Dados inválidos.", fields, status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        status_value = data.get("status")

        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response

        resume = get_resume_by_id_and_user(user_id, resume_id)
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        if status_value == "complete":
            merged = dict(data)
            if "targetPosition" not in merged:
                merged["targetPosition"] = resume.target_position
            if "contact" not in merged:
                try:
                    contact = resume.resumecontact
                except ResumeContact.DoesNotExist:
                    contact = None
                merged["contact"] = {
                    "fullName": contact.full_name if contact else "",
                    "email": contact.email if contact else "",
                }
            fields = validate_complete(merged)
            if fields:
                return _field_error("validation_error", "Dados inválidos.", fields, status.HTTP_400_BAD_REQUEST)

        resume = update_resume_draft(user_id, resume_id, data)
        if resume:
            maybe_create_version_after_save(user_id, resume_id)
            invalidate_dashboard_cache_for_user(user_id)
        return Response(resume_payload(resume), status=status.HTTP_200_OK)

    def delete(self, request, resume_id):
        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response

        deleted = delete_resume_soft(user_id, resume_id)
        if not deleted:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)
        invalidate_dashboard_cache_for_user(user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
