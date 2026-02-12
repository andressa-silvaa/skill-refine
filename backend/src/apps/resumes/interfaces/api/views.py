from __future__ import annotations

import logging
import os
import re
import socket
import subprocess
from datetime import date
from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from playwright.sync_api import Page

from apps.resumes.infrastructure.models import ResumeContact
from shared.api.responses import (
    error_response as _error,
    field_error_response as _field_error,
    serializer_field_errors as _serializer_field_errors,
)
from shared.auth.drf import request_meta

from .payloads import resume_detail_payload, resume_payload
from .pdf_browser import create_pdf_page
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

# Pagination: opt-in via ?limit=&offset=. When omitted, response is unchanged (compat).
PAGINATION_LIMIT_MIN = 1
PAGINATION_LIMIT_MAX = 100
PAGINATION_LIMIT_DEFAULT = 20
PAGINATION_OFFSET_DEFAULT = 0

PDF_RENDER_TIMEOUT_MS = 60000


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return cleaned or "Curriculo"


def _build_resume_pdf_from_preview(url: str) -> bytes:
    """
    Gera PDF a partir da URL de preview usando browser reutilizado.
    Usa uma nova página (tab) do browser singleton, mantendo o browser aberto.
    """
    logger = logging.getLogger(__name__)
    page: Page | None = None
    console_messages = []

    try:
        logger.info("Criando nova página no browser Playwright...")
        page = create_pdf_page(viewport={"width": 1280, "height": 720})
        logger.info("Página criada com sucesso")

        def handle_console(msg):
            console_messages.append(f"{msg.type}: {msg.text}")

        page.on("console", handle_console)

        logger.info(f"Navegando para URL: {url}")
        page.goto(url, wait_until="load", timeout=PDF_RENDER_TIMEOUT_MS)
        logger.info("Página carregada (evento 'load' disparado)")
        page.emulate_media(media="screen")
        logger.info("Media emulado como 'screen'")
        logger.info("Aguardando carregamento de fontes...")
        try:
            page.wait_for_function(
                "document.fonts && document.fonts.status === 'loaded'",
                timeout=10_000,
            )
            logger.info("Fontes carregadas")
        except Exception as e:
            logger.warning(f"Timeout ao aguardar fontes: {e}")

        logger.info("Aguardando sinal __resumePdfReady...")
        try:
            page.wait_for_function("window.__resumePdfReady === true", timeout=PDF_RENDER_TIMEOUT_MS)
            logger.info("Sinal __resumePdfReady recebido")
        except Exception as e:
            error = page.evaluate("window.__resumePdfError || null")
            if error:
                raise RuntimeError(f"Frontend error: {error}")
            page_state = page.evaluate("""
                () => ({
                    ready: window.__resumePdfReady,
                    error: window.__resumePdfError,
                    url: window.location.href,
                    hasData: document.querySelector('.sr-resume-print') !== null,
                    hasError: document.querySelector('.sr-resume-print__error') !== null,
                    hasLoading: document.querySelector('.sr-resume-print__loading') !== null,
                })
            """)
            console_log = "\n".join(console_messages[-10:])
            raise RuntimeError(
                f"PDF generation timeout. State: {page_state}. "
                f"Console: {console_log}. Original error: {str(e)}"
            )

        error = page.evaluate("window.__resumePdfError || null")
        if error:
            console_log = "\n".join(console_messages[-10:])
            logger.error(f"Erro reportado pelo frontend: {error}")
            logger.error(f"Console do navegador: {console_log}")
            raise RuntimeError(f"Frontend error: {error}. Console: {console_log}")

        logger.info("Gerando PDF...")
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        logger.info(f"PDF gerado: {len(pdf_bytes)} bytes")

        return pdf_bytes
    finally:
        if page:
            try:
                page.close()
            except Exception:
                pass


class ResumeListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        limit_param = request.query_params.get("limit")
        offset_param = request.query_params.get("offset")

        if limit_param is None and offset_param is None:
            items = list_resumes(user_id)
            return Response({"items": [resume_payload(r) for r in items]}, status=status.HTTP_200_OK)

        try:
            limit = int(limit_param) if limit_param not in (None, "") else PAGINATION_LIMIT_DEFAULT
        except ValueError:
            limit = None
        try:
            offset = int(offset_param) if offset_param not in (None, "") else PAGINATION_OFFSET_DEFAULT
        except ValueError:
            offset = -1

        if limit is None or limit < PAGINATION_LIMIT_MIN or limit > PAGINATION_LIMIT_MAX:
            return _error(
                "validation_error",
                f"Parâmetro limit deve ser um número entre {PAGINATION_LIMIT_MIN} e {PAGINATION_LIMIT_MAX}.",
                status.HTTP_400_BAD_REQUEST,
            )
        if offset < 0:
            return _error(
                "validation_error",
                "Parâmetro offset deve ser um número maior ou igual a 0.",
                status.HTTP_400_BAD_REQUEST,
            )

        page, total = list_resumes_paginated(user_id, limit, offset)
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

        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        _ = request_meta(request)

        resume = create_resume_draft(user_id, data)
        return Response(resume_payload(resume), status=status.HTTP_201_CREATED)


class ResumeDraftUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

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

        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

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
        return Response(resume_payload(resume), status=status.HTTP_200_OK)

    def delete(self, request, resume_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        deleted = delete_resume_soft(user_id, resume_id)
        if not deleted:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResumeDuplicateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, resume_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        new_resume = duplicate_resume(user_id, resume_id)
        if not new_resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        return Response(resume_payload(new_resume), status=status.HTTP_201_CREATED)


class ResumePdfTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

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


class ResumePdfView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        resume = get_resume_by_id_and_user(user_id, resume_id)
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        logger = logging.getLogger(__name__)
        token = create_pdf_token(str(resume.id), str(user_id))
        frontend_url = settings.FRONTEND_URL.rstrip("/")

        is_docker = os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")

        if is_docker and (
            frontend_url.startswith("http://localhost") or frontend_url.startswith("http://127.0.0.1")
        ):
            try:
                socket.create_connection(("host.docker.internal", 3000), timeout=2).close()
                frontend_url = frontend_url.replace("localhost", "host.docker.internal").replace(
                    "127.0.0.1", "host.docker.internal"
                )
                logger.info("Usando host.docker.internal para acessar frontend")
            except (socket.error, socket.timeout):
                try:
                    gateway_ip = socket.gethostbyname("host.docker.internal")
                    frontend_url = frontend_url.replace("localhost", gateway_ip).replace(
                        "127.0.0.1", gateway_ip
                    )
                    logger.info(f"Usando gateway IP {gateway_ip} para acessar frontend")
                except socket.gaierror:
                    try:
                        result = subprocess.run(
                            ["ip", "route", "show", "default"],
                            capture_output=True,
                            text=True,
                            timeout=2,
                        )
                        if result.returncode == 0:
                            gateway = result.stdout.split()[2]
                            frontend_url = frontend_url.replace("localhost", gateway).replace(
                                "127.0.0.1", gateway
                            )
                            logger.info(f"Usando Docker gateway {gateway} para acessar frontend")
                    except Exception as e:
                        logger.warning(f"Não foi possível detectar IP do host: {e}. Usando localhost.")

        backend_url = "http://localhost:8000"
        print_url = frontend_url + f"/resume/print/{resume.id}?token={quote(token)}&apiUrl={quote(backend_url)}"

        try:
            logger.info(f"Gerando PDF para currículo {resume.id}")
            logger.info(f"URL de print: {print_url}")
            pdf_bytes = _build_resume_pdf_from_preview(print_url)
            logger.info(f"PDF gerado com sucesso ({len(pdf_bytes)} bytes)")
        except Exception as e:
            import traceback

            error_msg = str(e)
            stack_trace = traceback.format_exc()
            logger.error(f"Erro ao gerar PDF: {error_msg}")
            logger.error(f"Stack trace: {stack_trace}")
            logger.error(f"URL tentada: {print_url}")
            return _error(
                "pdf_generation_failed",
                f"Não foi possível gerar o PDF. Verifique se o frontend está acessível e os logs do backend para mais detalhes. Erro: {error_msg}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        safe_name = _safe_filename(resume.name or resume.target_position or "Curriculo")
        filename = f"Curriculo_{safe_name}_{date.today().isoformat()}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
