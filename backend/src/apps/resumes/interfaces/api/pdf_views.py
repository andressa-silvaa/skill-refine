"""PDF export views: start, status, download."""
from __future__ import annotations

import logging
import time

from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api.responses import error_response as _error

from .pdf_exports import (
    build_pdf_filename,
    build_pdf_status_payload,
    get_or_request_pdf_export,
    get_ready_export_by_id,
    maybe_recover_export,
    read_export_file,
)
from .services import get_resume_by_id_and_user
from .view_helpers import require_user_id

logger = logging.getLogger(__name__)


class ResumePdfView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_id):
        request_start = time.perf_counter()
        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response

        resume = get_resume_by_id_and_user(user_id, resume_id)
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        export_id = (request.query_params.get("export_id") or "").strip()
        if export_id:
            export = get_ready_export_by_id(str(user_id), str(resume.id), export_id)
            if not export:
                return _error(
                    "pdf_not_ready",
                    "PDF ainda não está pronto para download.",
                    status.HTTP_409_CONFLICT,
                )
        else:
            stage, export, _, _ = get_or_request_pdf_export(resume, str(user_id))
            if stage != "ready":
                payload = build_pdf_status_payload(resume, export, cache_hit=False)
                return Response(payload, status=status.HTTP_202_ACCEPTED)

        try:
            pdf_bytes = read_export_file(export.storage_path)
        except Exception:
            return _error(
                "pdf_generation_failed",
                "Não foi possível carregar o PDF gerado.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        filename = build_pdf_filename(resume)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        logger.info(
            "Resume PDF download served",
            extra={
                "resume_id": str(resume.id),
                "user_id": str(user_id),
                "export_id": str(export.id),
                "request_total_ms": int((time.perf_counter() - request_start) * 1000),
            },
        )
        return response


class ResumePdfStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "pdf_export_start"

    def post(self, request, resume_id):
        request_start = time.perf_counter()
        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response

        resume = get_resume_by_id_and_user(user_id, resume_id)
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        stage, export, _, telemetry = get_or_request_pdf_export(resume, str(user_id))
        payload = build_pdf_status_payload(resume, export, cache_hit=bool(telemetry.get("cache_hit")))
        logger.info(
            "Resume PDF start",
            extra={
                "resume_id": str(resume.id),
                "user_id": str(user_id),
                "export_id": str(export.id),
                "status": payload.get("status"),
                "cache_hit": bool(telemetry.get("cache_hit")),
                "request_total_ms": int((time.perf_counter() - request_start) * 1000),
            },
        )
        status_code = status.HTTP_200_OK if stage == "ready" else status.HTTP_202_ACCEPTED
        return Response(payload, status=status_code)


class ResumePdfStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "pdf_export_status"

    def get(self, request, resume_id, export_id):
        user_id, error_response = require_user_id(request)
        if error_response:
            return error_response

        resume = get_resume_by_id_and_user(user_id, resume_id)
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        from apps.resumes.infrastructure.models import ResumeExport, ResumeExportType

        export = ResumeExport.objects.filter(
            id=export_id,
            resume_id=resume.id,
            user_id=user_id,
            export_type=ResumeExportType.PDF,
        ).first()
        if not export:
            return _error("not_found", "Exportação não encontrada.", status.HTTP_404_NOT_FOUND)

        export = maybe_recover_export(export)
        payload = build_pdf_status_payload(resume, export, cache_hit=False)
        if payload.get("status") == "pending":
            return Response(payload, status=status.HTTP_202_ACCEPTED)
        return Response(payload, status=status.HTTP_200_OK)
