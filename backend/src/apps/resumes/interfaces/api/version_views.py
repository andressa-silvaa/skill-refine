from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api.responses import error_response as _error

from .payloads import resume_payload, version_detail_payload, version_list_item_payload
from .view_helpers import (
    invalidate_dashboard_cache_for_user,
    parse_limit_offset,
    require_user_id,
)
from .version_services import (
    get_version_by_id,
    list_versions,
    list_versions_paginated,
    restore_version,
)

VERSIONS_LIMIT_MIN = 1
VERSIONS_LIMIT_MAX = 100
VERSIONS_LIMIT_DEFAULT = 20
VERSIONS_OFFSET_DEFAULT = 0


class ResumeVersionListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response
        resume_id = request.query_params.get("resume_id")
        limit_param = request.query_params.get("limit")
        offset_param = request.query_params.get("offset")

        if limit_param is None and offset_param is None:
            qs = list_versions(user_id, resume_id=resume_id)
            items = [version_list_item_payload(v) for v in qs]
            return Response({"items": items}, status=status.HTTP_200_OK)

        page_params, page_error = parse_limit_offset(
            limit_param=limit_param,
            offset_param=offset_param,
            limit_default=VERSIONS_LIMIT_DEFAULT,
            offset_default=VERSIONS_OFFSET_DEFAULT,
            limit_min=VERSIONS_LIMIT_MIN,
            limit_max=VERSIONS_LIMIT_MAX,
        )
        if page_error:
            return page_error
        limit, offset = page_params

        page, total = list_versions_paginated(user_id, limit, offset, resume_id=resume_id)
        next_offset = offset + limit
        has_next = next_offset < total
        payload = {
            "items": [version_list_item_payload(v) for v in page],
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_next": has_next,
            "next_offset": next_offset if has_next else None,
        }
        return Response(payload, status=status.HTTP_200_OK)


class ResumeVersionDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_id, version_id):
        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response
        version = get_version_by_id(user_id, resume_id, version_id)
        if not version:
            return _error("not_found", "Versão não encontrada.", status.HTTP_404_NOT_FOUND)
        return Response(version_detail_payload(version), status=status.HTTP_200_OK)


class ResumeVersionRestoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, resume_id, version_id):
        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response
        resume = restore_version(user_id, resume_id, version_id)
        if not resume:
            return _error("not_found", "Versão ou currículo não encontrado.", status.HTTP_404_NOT_FOUND)
        invalidate_dashboard_cache_for_user(user_id)
        return Response(resume_payload(resume), status=status.HTTP_200_OK)
