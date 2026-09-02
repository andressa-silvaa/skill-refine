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

class ResumeDuplicateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, resume_id):
        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response

        new_resume = duplicate_resume(user_id, resume_id)
        if not new_resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)
        invalidate_dashboard_cache_for_user(user_id)

        return Response(resume_payload(new_resume), status=status.HTTP_201_CREATED)


class ResumePdfTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_id):
        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response

        resume = get_resume_by_id_and_user(user_id, resume_id)
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        token = create_pdf_token(str(resume.id), str(user_id))
        return Response({"token": token}, status=status.HTTP_200_OK)


class ResumePdfDataView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, resume_id):
        token = (request.query_params.get("token") or "").strip()
        payload = parse_pdf_token(token)
        if not payload:
            return _error("invalid_token", "Token inválido.", status.HTTP_401_UNAUTHORIZED)

        if payload.get("resume_id") != str(resume_id):
            return _error("invalid_token", "Token inválido.", status.HTTP_401_UNAUTHORIZED)

        resume = get_resume_for_pdf_data(resume_id, payload.get("user_id", ""))
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        return Response(resume_detail_payload(resume), status=status.HTTP_200_OK)
