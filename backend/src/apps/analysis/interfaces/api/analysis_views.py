from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api.responses import (
    error_response as _error,
    field_error_response as _field_error,
    serializer_field_errors as _serializer_field_errors,
)

from .payloads import analysis_payload
from .serializers import RunAnalysisSerializer
from .services import (
    get_latest_analysis,
    get_latest_analyses_map,
    list_analysis_history,
    run_analysis,
    validate_resume_ownership,
)

HISTORY_LIMIT_MAX = 100
HISTORY_LIMIT_DEFAULT = 20

# Latest/history must not be cached by proxies or browsers (resume edits change validity immediately).
_ANALYSIS_READ_HEADERS = {"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"}


def _require_user_id(request):
    user_id = getattr(request.user, "id", None)
    if not user_id:
        return None, _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)
    return str(user_id), None


def _parse_history_pagination(request):
    limit_param = request.query_params.get("limit", HISTORY_LIMIT_DEFAULT)
    offset_param = request.query_params.get("offset", 0)
    try:
        limit = int(limit_param) if limit_param not in (None, "") else HISTORY_LIMIT_DEFAULT
    except (TypeError, ValueError):
        limit = HISTORY_LIMIT_DEFAULT
    try:
        offset = int(offset_param) if offset_param not in (None, "") else 0
    except (TypeError, ValueError):
        offset = 0

    if limit < 1 or limit > HISTORY_LIMIT_MAX:
        return None, _error(
            "validation_error",
            f"Parâmetro limit deve ser entre 1 e {HISTORY_LIMIT_MAX}.",
            status.HTTP_400_BAD_REQUEST,
        )
    if offset < 0:
        return None, _error(
            "validation_error",
            "Parâmetro offset deve ser maior ou igual a 0.",
            status.HTTP_400_BAD_REQUEST,
        )
    return (limit, offset), None


class RunAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "analysis"

    def post(self, request):
        user_id, auth_error = _require_user_id(request)
        if auth_error:
            return auth_error

        ser = RunAnalysisSerializer(data=request.data)
        if not ser.is_valid():
            fields = _serializer_field_errors(ser)
            return _field_error(
                "validation_error",
                "Dados inválidos.",
                fields,
                status.HTTP_400_BAD_REQUEST,
            )

        data = ser.validated_data
        resume_id = data["resume_id"]
        job_description_text = data.get("job_description_text") or ""

        analysis, err = run_analysis(
            user_id,
            resume_id,
            job_description_text.strip() or None,
        )
        if err == "not_found":
            return _error(
                "not_found",
                "Currículo não encontrado ou você não tem permissão para analisá-lo.",
                status.HTTP_404_NOT_FOUND,
            )
        if err == "unavailable":
            return _error(
                "service_unavailable",
                "Análise indisponível no momento. Tente novamente em instantes.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            analysis_payload(analysis),
            status=status.HTTP_202_ACCEPTED,
        )


class LatestAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "analysis"

    def get(self, request):
        user_id, auth_error = _require_user_id(request)
        if auth_error:
            return auth_error

        resume_ids_raw = (request.query_params.get("resume_ids") or "").strip()
        if resume_ids_raw:
            resume_ids = [segment.strip() for segment in resume_ids_raw.split(",") if segment.strip()]
            resume_ids = resume_ids[:100]
            latest_map = get_latest_analyses_map(user_id, resume_ids)
            payload = {resume_id: analysis_payload(latest_map[resume_id]) for resume_id in latest_map}
            return Response(
                {"items": payload},
                status=status.HTTP_200_OK,
                headers=_ANALYSIS_READ_HEADERS,
            )

        resume_id = (request.query_params.get("resume_id") or "").strip()
        if not resume_id:
            return _error(
                "validation_error",
                "Parâmetro resume_id é obrigatório.",
                status.HTTP_400_BAD_REQUEST,
            )

        if not validate_resume_ownership(user_id, resume_id):
            return _error(
                "not_found",
                "Currículo não encontrado ou você não tem permissão para acessá-lo.",
                status.HTTP_404_NOT_FOUND,
            )

        analysis = get_latest_analysis(user_id, resume_id)
        if analysis is None:
            return Response(
                {"item": None},
                status=status.HTTP_200_OK,
                headers=_ANALYSIS_READ_HEADERS,
            )

        return Response(
            {"item": analysis_payload(analysis)},
            status=status.HTTP_200_OK,
            headers=_ANALYSIS_READ_HEADERS,
        )


class HistoryAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "analysis"

    def get(self, request):
        user_id, auth_error = _require_user_id(request)
        if auth_error:
            return auth_error

        resume_id = (request.query_params.get("resume_id") or "").strip()
        if not resume_id:
            return _error(
                "validation_error",
                "Parâmetro resume_id é obrigatório.",
                status.HTTP_400_BAD_REQUEST,
            )

        if not validate_resume_ownership(user_id, resume_id):
            return _error(
                "not_found",
                "Currículo não encontrado ou você não tem permissão para acessá-lo.",
                status.HTTP_404_NOT_FOUND,
            )

        page_params, page_error = _parse_history_pagination(request)
        if page_error:
            return page_error
        limit, offset = page_params

        page, total = list_analysis_history(user_id, resume_id.strip(), limit=limit, offset=offset)
        next_offset = offset + limit
        has_next = next_offset < total

        return Response(
            {
                "items": [analysis_payload(a) for a in page],
                "limit": limit,
                "offset": offset,
                "total": total,
                "hasNext": has_next,
                "nextOffset": next_offset if has_next else None,
            },
            status=status.HTTP_200_OK,
            headers=_ANALYSIS_READ_HEADERS,
        )
