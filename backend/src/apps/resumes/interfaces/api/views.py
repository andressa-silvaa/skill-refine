from __future__ import annotations

from datetime import date
import re
from typing import Any, Iterable
from urllib.parse import quote

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from playwright.sync_api import Page

from apps.resumes.infrastructure.models import (
    Resume,
    ResumeContact,
    ResumeEducation,
    ResumeExperience,
    ResumeExperienceBullet,
    ResumeLanguage,
    ResumeSectionOrder,
    ResumeSkill,
    ResumeStatus,
    ResumeTag,
)
from shared.auth.drf import request_meta

from .serializers import ResumeDraftSerializer
from .pdf_browser import create_pdf_page


def _canonical_error_code(code: str) -> str:
    return (code or "").strip().upper()


def _error(code: str, message: str, http_status: int) -> Response:
    canonical = _canonical_error_code(code)
    payload = {
        "error": {"code": code, "error_code": canonical, "message": message},
        "error_code": canonical,
        "message": message,
    }
    return Response(payload, status=http_status)


def _field_error(code: str, message: str, fields: dict[str, str], http_status: int) -> Response:
    canonical = _canonical_error_code(code)
    payload = {
        "error": {"code": code, "error_code": canonical, "message": message},
        "error_code": canonical,
        "message": message,
        "fields": fields,
    }
    return Response(payload, status=http_status)


def _extract_error_message(value: Any) -> str:
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
        return _extract_error_message(first)
    return str(value)


def _serializer_field_errors(serializer) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key, val in serializer.errors.items():
        if not key:
            continue
        fields[key] = _extract_error_message(val)
    return fields


def _parse_month(value: str | None) -> date | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    parts = raw.split("-")
    if len(parts) != 2:
        return None
    year_str, month_str = parts
    try:
        year = int(year_str)
        month = int(month_str)
    except ValueError:
        return None
    if month < 1 or month > 12:
        return None
    return date(year, month, 1)


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def _resume_payload(resume: Resume) -> dict[str, Any]:
    tags = list(
        ResumeTag.objects.filter(resume=resume)
        .order_by("position_index")
        .values_list("label", flat=True)
    )
    status_value = resume.status
    if status_value not in (ResumeStatus.DRAFT, ResumeStatus.COMPLETE, ResumeStatus.ANALYZING):
        status_value = ResumeStatus.DRAFT
    return {
        "id": str(resume.id),
        "name": resume.name or resume.target_position or "Novo Currículo",
        "updatedAt": resume.updated_at.isoformat(),
        "status": status_value,
        "score": resume.score or 0,
        "tags": tags,
    }


def _unique_copy_name(user_id: str, base_name: str) -> str:
    base = base_name.strip() or "Currículo"
    candidate = f"Cópia de {base}"
    if not Resume.objects.filter(user_id=user_id, name=candidate, deleted_at__isnull=True).exists():
        return candidate


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return cleaned or "Curriculo"


PDF_TOKEN_SALT = "resume-pdf"
PDF_TOKEN_TTL_SECONDS = 120
PDF_RENDER_TIMEOUT_MS = 60000


def _create_pdf_token(resume_id: str, user_id: str) -> str:
    return signing.dumps({"resume_id": resume_id, "user_id": user_id}, salt=PDF_TOKEN_SALT)


def _parse_pdf_token(token: str | None) -> dict[str, str] | None:
    if not token:
        return None
    try:
        data = signing.loads(token, salt=PDF_TOKEN_SALT, max_age=PDF_TOKEN_TTL_SECONDS)
    except signing.SignatureExpired:
        return None
    except signing.BadSignature:
        return None
    if not isinstance(data, dict):
        return None
    resume_id = str(data.get("resume_id") or "").strip()
    user_id = str(data.get("user_id") or "").strip()
    if not resume_id or not user_id:
        return None
    return {"resume_id": resume_id, "user_id": user_id}


def _section_order(resume: Resume) -> list[str]:
    orders = list(
        ResumeSectionOrder.objects.filter(resume=resume, is_visible=True).order_by("position_index")
    )
    if orders:
        return [order.section_key for order in orders]
    return ["summary", "experience", "education", "skills", "languages", "contact"]


def _build_resume_pdf_from_preview(url: str) -> bytes:
    """
    Gera PDF a partir da URL de preview usando browser reutilizado.
    Usa uma nova página (tab) do browser singleton, mantendo o browser aberto.
    """
    page: Page | None = None
    console_messages = []
    
    try:
        # Cria nova página no browser singleton (não fecha o browser)
        page = create_pdf_page(viewport={"width": 1280, "height": 720})
        
        def handle_console(msg):
            console_messages.append(f"{msg.type}: {msg.text}")
        
        page.on("console", handle_console)
        
        # "networkidle" pode demorar muito (especialmente com polling/requests longas).
        # Como já aguardamos um sinal explícito de prontidão (__resumePdfReady),
        # basta "load" para iniciar e depois aguardar o ready.
        page.goto(url, wait_until="load", timeout=PDF_RENDER_TIMEOUT_MS)
        page.emulate_media(media="screen")
        # Fonts podem ser lentas; não vale segurar o PDF por 60s só por isso.
        # Tentamos aguardar um pouco e seguimos mesmo em timeout.
        try:
            page.wait_for_function(
                "document.fonts && document.fonts.status === 'loaded'",
                timeout=10_000,
            )
        except Exception:
            pass
        
        # Aguardar o ready ou error
        try:
            page.wait_for_function("window.__resumePdfReady === true", timeout=PDF_RENDER_TIMEOUT_MS)
        except Exception as e:
            # Se timeout, verificar se há erro
            error = page.evaluate("window.__resumePdfError || null")
            if error:
                raise RuntimeError(f"Frontend error: {error}")
            # Se não há erro mas não ficou ready, verificar o estado da página
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
            console_log = "\n".join(console_messages[-10:])  # Últimas 10 mensagens
            raise RuntimeError(
                f"PDF generation timeout. State: {page_state}. "
                f"Console: {console_log}. Original error: {str(e)}"
            )
        
        error = page.evaluate("window.__resumePdfError || null")
        if error:
            console_log = "\n".join(console_messages[-10:])
            raise RuntimeError(f"Frontend error: {error}. Console: {console_log}")
        
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        
        return pdf_bytes
    finally:
        # Fecha apenas a página, não o browser
        if page:
            try:
                page.close()
            except Exception:
                pass  # Ignora erros ao fechar página


def _format_month(value: date | None) -> str:
    if not value:
        return ""
    return value.strftime("%Y-%m")


def _resume_detail_payload(resume: Resume) -> dict[str, Any]:
    contact = ResumeContact.objects.filter(resume=resume).first()
    experiences = (
        ResumeExperience.objects.filter(resume=resume)
        .order_by("position_index")
    )
    educations = (
        ResumeEducation.objects.filter(resume=resume)
        .order_by("position_index")
    )
    skills = (
        ResumeSkill.objects.filter(resume=resume)
        .order_by("position_index")
    )
    languages = (
        ResumeLanguage.objects.filter(resume=resume)
        .order_by("position_index")
    )

    exp_payload = []
    for exp in experiences:
        bullets = list(
            ResumeExperienceBullet.objects.filter(experience=exp)
            .order_by("position_index")
            .values_list("content", flat=True)
        )
        exp_payload.append(
            {
                "id": str(exp.id),
                "company": exp.company or "",
                "position": exp.position or "",
                "startDate": _format_month(exp.start_date),
                "endDate": _format_month(exp.end_date),
                "isCurrent": bool(exp.is_current),
                "description": bullets,
            }
        )

    edu_payload = [
        {
            "id": str(edu.id),
            "institution": edu.institution or "",
            "course": edu.course or "",
            "degree": edu.degree or "",
            "startDate": _format_month(edu.start_date),
            "endDate": _format_month(edu.end_date),
            "status": edu.status,
        }
        for edu in educations
    ]

    skill_payload = [
        {
            "id": str(skill.id),
            "name": skill.name or "",
            "level": skill.level or None,
        }
        for skill in skills
    ]

    lang_payload = [
        {
            "id": str(lang.id),
            "name": lang.name or "",
            "level": lang.level,
        }
        for lang in languages
    ]

    return {
        "id": str(resume.id),
        "name": resume.name or resume.target_position or "Novo Currículo",
        "status": resume.status,
        "updatedAt": resume.updated_at.isoformat(),
        "lastStep": resume.last_step,
        "data": {
            "themeId": resume.theme_id,
            "themePaletteId": resume.theme_palette_id or "",
            "themeAccentOverride": resume.theme_accent_override or "",
            "themeSecondaryOverride": resume.theme_secondary_override or "",
            "targetPosition": resume.target_position or "",
            "summary": resume.summary or "",
            "contact": {
                "fullName": contact.full_name or "" if contact else "",
                "email": contact.email or "" if contact else "",
                "phone": contact.phone or "" if contact else "",
                "city": contact.city or "" if contact else "",
                "country": contact.country or "" if contact else "",
                "linkedin": contact.linkedin or "" if contact else "",
                "portfolio": contact.portfolio or "" if contact else "",
                "github": contact.github or "" if contact else "",
                "website": contact.website or "" if contact else "",
            },
            "experiences": exp_payload,
            "educations": edu_payload,
            "skills": skill_payload,
            "languages": lang_payload,
        },
    }


def _validate_complete(data: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    target_position = (data.get("targetPosition") or "").strip()
    contact = data.get("contact") or {}
    full_name = (contact.get("fullName") or "").strip()
    email = (contact.get("email") or "").strip()
    if not target_position:
        fields["targetPosition"] = "Informe o cargo alvo."
    if not full_name:
        fields["contact.fullName"] = "Informe o nome completo."
    if not email:
        fields["contact.email"] = "Informe o e-mail."
    return fields


def _replace_experiences(resume: Resume, experiences: Iterable[dict[str, Any]]) -> None:
    ResumeExperience.objects.filter(resume=resume).delete()
    for idx, exp in enumerate(experiences):
        exp_obj = ResumeExperience.objects.create(
            resume=resume,
            company=exp.get("company") or "",
            position=exp.get("position") or "",
            start_date=_parse_month(exp.get("startDate")),
            end_date=_parse_month(exp.get("endDate")),
            is_current=bool(exp.get("isCurrent")),
            position_index=idx,
        )
        bullets = exp.get("description") or []
        for b_idx, content in enumerate(bullets):
            ResumeExperienceBullet.objects.create(
                experience=exp_obj,
                content=str(content or ""),
                position_index=b_idx,
            )


def _replace_educations(resume: Resume, educations: Iterable[dict[str, Any]]) -> None:
    ResumeEducation.objects.filter(resume=resume).delete()
    for idx, edu in enumerate(educations):
        ResumeEducation.objects.create(
            resume=resume,
            institution=edu.get("institution") or "",
            course=edu.get("course") or "",
            degree=edu.get("degree") or "",
            start_date=_parse_month(edu.get("startDate")),
            end_date=_parse_month(edu.get("endDate")),
            status=edu.get("status") or "completed",
            position_index=idx,
        )


def _replace_skills(resume: Resume, skills: Iterable[dict[str, Any]]) -> None:
    ResumeSkill.objects.filter(resume=resume).delete()
    for idx, skill in enumerate(skills):
        ResumeSkill.objects.create(
            resume=resume,
            name=skill.get("name") or "",
            level=skill.get("level") or None,
            position_index=idx,
        )


def _replace_languages(resume: Resume, languages: Iterable[dict[str, Any]]) -> None:
    ResumeLanguage.objects.filter(resume=resume).delete()
    for idx, lang in enumerate(languages):
        ResumeLanguage.objects.create(
            resume=resume,
            name=lang.get("name") or "",
            level=lang.get("level") or "intermediate",
            position_index=idx,
        )


class ResumeListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)
        items = (
            Resume.objects.filter(user_id=user_id, deleted_at__isnull=True)
            .order_by("-updated_at")
        )
        return Response({"items": [_resume_payload(r) for r in items]}, status=status.HTTP_200_OK)

    def post(self, request):
        ser = ResumeDraftSerializer(data=request.data)
        if not ser.is_valid():
            fields = _serializer_field_errors(ser)
            return _field_error("validation_error", "Dados inválidos.", fields, status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        status_value = data.get("status") or "draft"
        if status_value == "complete":
            fields = _validate_complete(data)
            if fields:
                return _field_error("validation_error", "Dados inválidos.", fields, status.HTTP_400_BAD_REQUEST)

        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        _ = request_meta(request)

        with transaction.atomic():
            resume = Resume.objects.create(
                user_id=user_id,
                name=(data.get("name") or "").strip(),
                status=ResumeStatus.COMPLETE if status_value == "complete" else ResumeStatus.DRAFT,
                last_step=(data.get("lastStep") or "").strip() or None,
                target_position=(data.get("targetPosition") or "").strip(),
                summary=(data.get("summary") or "").strip(),
                theme_id=(data.get("themeId") or "").strip() or "classic-one-column",
                theme_palette_id=_normalize_optional(data.get("themePaletteId")),
                theme_accent_override=_normalize_optional(data.get("themeAccentOverride")),
                theme_secondary_override=_normalize_optional(data.get("themeSecondaryOverride")),
            )

            contact = data.get("contact")
            if contact is not None:
                ResumeContact.objects.update_or_create(
                    resume=resume,
                    defaults={
                        "full_name": contact.get("fullName") or "",
                        "email": contact.get("email") or "",
                        "phone": contact.get("phone") or "",
                        "city": contact.get("city") or "",
                        "country": contact.get("country") or "",
                        "linkedin": _normalize_optional(contact.get("linkedin")),
                        "portfolio": _normalize_optional(contact.get("portfolio")),
                        "github": _normalize_optional(contact.get("github")),
                        "website": _normalize_optional(contact.get("website")),
                    },
                )

            if "experiences" in data:
                _replace_experiences(resume, data.get("experiences") or [])
            if "educations" in data:
                _replace_educations(resume, data.get("educations") or [])
            if "skills" in data:
                _replace_skills(resume, data.get("skills") or [])
            if "languages" in data:
                _replace_languages(resume, data.get("languages") or [])

        return Response(_resume_payload(resume), status=status.HTTP_201_CREATED)


class ResumeDraftUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        resume = Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True).first()
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        return Response(_resume_detail_payload(resume), status=status.HTTP_200_OK)

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

        resume = Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True).first()
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        if status_value == "complete":
            merged = dict(data)
            if "targetPosition" not in merged:
                merged["targetPosition"] = resume.target_position
            if "contact" not in merged:
                contact = ResumeContact.objects.filter(resume=resume).first()
                merged["contact"] = {
                    "fullName": contact.full_name if contact else "",
                    "email": contact.email if contact else "",
                }
            fields = _validate_complete(merged)
            if fields:
                return _field_error("validation_error", "Dados inválidos.", fields, status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if "name" in data:
                resume.name = (data.get("name") or "").strip()
            if "targetPosition" in data:
                resume.target_position = (data.get("targetPosition") or "").strip()
            if "summary" in data:
                resume.summary = (data.get("summary") or "").strip()
            if "themeId" in data:
                resume.theme_id = (data.get("themeId") or "").strip() or resume.theme_id
            if "themePaletteId" in data:
                resume.theme_palette_id = _normalize_optional(data.get("themePaletteId"))
            if "themeAccentOverride" in data:
                resume.theme_accent_override = _normalize_optional(data.get("themeAccentOverride"))
            if "themeSecondaryOverride" in data:
                resume.theme_secondary_override = _normalize_optional(data.get("themeSecondaryOverride"))
            if "lastStep" in data:
                resume.last_step = (data.get("lastStep") or "").strip() or None
            if status_value == "complete":
                resume.status = ResumeStatus.COMPLETE
            elif status_value == "draft":
                resume.status = ResumeStatus.DRAFT

            resume.save()

            if "contact" in data:
                contact = data.get("contact") or {}
                ResumeContact.objects.update_or_create(
                    resume=resume,
                    defaults={
                        "full_name": contact.get("fullName") or "",
                        "email": contact.get("email") or "",
                        "phone": contact.get("phone") or "",
                        "city": contact.get("city") or "",
                        "country": contact.get("country") or "",
                        "linkedin": _normalize_optional(contact.get("linkedin")),
                        "portfolio": _normalize_optional(contact.get("portfolio")),
                        "github": _normalize_optional(contact.get("github")),
                        "website": _normalize_optional(contact.get("website")),
                    },
                )

            if "experiences" in data:
                _replace_experiences(resume, data.get("experiences") or [])
            if "educations" in data:
                _replace_educations(resume, data.get("educations") or [])
            if "skills" in data:
                _replace_skills(resume, data.get("skills") or [])
            if "languages" in data:
                _replace_languages(resume, data.get("languages") or [])

        return Response(_resume_payload(resume), status=status.HTTP_200_OK)

    def delete(self, request, resume_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        resume = Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True).first()
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        resume.deleted_at = timezone.now()
        resume.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResumeDuplicateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, resume_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        resume = Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True).first()
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        contact = ResumeContact.objects.filter(resume=resume).first()
        experiences = list(ResumeExperience.objects.filter(resume=resume).order_by("position_index"))
        educations = list(ResumeEducation.objects.filter(resume=resume).order_by("position_index"))
        skills = list(ResumeSkill.objects.filter(resume=resume).order_by("position_index"))
        languages = list(ResumeLanguage.objects.filter(resume=resume).order_by("position_index"))
        tags = list(ResumeTag.objects.filter(resume=resume).order_by("position_index"))
        section_orders = list(ResumeSectionOrder.objects.filter(resume=resume).order_by("position_index"))

        with transaction.atomic():
            copy_name = _unique_copy_name(user_id, resume.name or resume.target_position or "Currículo")
            new_resume = Resume.objects.create(
                user_id=user_id,
                name=copy_name,
                status=ResumeStatus.DRAFT,
                target_position=resume.target_position,
                summary=resume.summary,
                theme_id=resume.theme_id,
                theme_palette_id=resume.theme_palette_id,
                theme_accent_override=resume.theme_accent_override,
                theme_secondary_override=resume.theme_secondary_override,
                last_step=resume.last_step,
                score=None,
            )

            if contact:
                ResumeContact.objects.create(
                    resume=new_resume,
                    full_name=contact.full_name,
                    email=contact.email,
                    phone=contact.phone,
                    city=contact.city,
                    country=contact.country,
                    linkedin=contact.linkedin,
                    portfolio=contact.portfolio,
                    github=contact.github,
                    website=contact.website,
                )

            for exp in experiences:
                new_exp = ResumeExperience.objects.create(
                    resume=new_resume,
                    company=exp.company,
                    position=exp.position,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    is_current=exp.is_current,
                    position_index=exp.position_index,
                )
                bullets = ResumeExperienceBullet.objects.filter(experience=exp).order_by("position_index")
                for bullet in bullets:
                    ResumeExperienceBullet.objects.create(
                        experience=new_exp,
                        content=bullet.content,
                        position_index=bullet.position_index,
                    )

            for edu in educations:
                ResumeEducation.objects.create(
                    resume=new_resume,
                    institution=edu.institution,
                    course=edu.course,
                    degree=edu.degree,
                    start_date=edu.start_date,
                    end_date=edu.end_date,
                    status=edu.status,
                    position_index=edu.position_index,
                )

            for skill in skills:
                ResumeSkill.objects.create(
                    resume=new_resume,
                    name=skill.name,
                    level=skill.level,
                    position_index=skill.position_index,
                )

            for lang in languages:
                ResumeLanguage.objects.create(
                    resume=new_resume,
                    name=lang.name,
                    level=lang.level,
                    position_index=lang.position_index,
                )

            for tag in tags:
                ResumeTag.objects.create(
                    resume=new_resume,
                    label=tag.label,
                    position_index=tag.position_index,
                )

            for order in section_orders:
                ResumeSectionOrder.objects.create(
                    resume=new_resume,
                    section_key=order.section_key,
                    position_index=order.position_index,
                    is_visible=order.is_visible,
                )

        return Response(_resume_payload(new_resume), status=status.HTTP_201_CREATED)


class ResumePdfTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        resume = Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True).first()
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        token = _create_pdf_token(str(resume.id), str(user_id))
        return Response({"token": token}, status=status.HTTP_200_OK)


class ResumePdfDataView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, resume_id):
        token = (request.query_params.get("token") or "").strip()
        payload = _parse_pdf_token(token)
        if not payload:
            return _error("invalid_token", "Token inválido.", status.HTTP_401_UNAUTHORIZED)

        if payload.get("resume_id") != str(resume_id):
            return _error("invalid_token", "Token inválido.", status.HTTP_401_UNAUTHORIZED)

        resume = Resume.objects.filter(
            id=resume_id,
            user_id=payload.get("user_id"),
            deleted_at__isnull=True,
        ).first()
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        return Response(_resume_detail_payload(resume), status=status.HTTP_200_OK)


class ResumePdfView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resume_id):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        resume = Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True).first()
        if not resume:
            return _error("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)

        token = _create_pdf_token(str(resume.id), str(user_id))
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        # Se estiver rodando dentro do Docker e a URL for localhost, usar host.docker.internal
        if frontend_url.startswith("http://localhost") or frontend_url.startswith("http://127.0.0.1"):
            frontend_url = frontend_url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
        # URL do backend que o frontend deve usar quando renderizado pelo Playwright
        # O Playwright está rodando dentro do container do backend, então localhost:8000 funciona
        backend_url = "http://localhost:8000"
        print_url = frontend_url + f"/resume/print/{resume.id}?token={quote(token)}&apiUrl={quote(backend_url)}"

        try:
            pdf_bytes = _build_resume_pdf_from_preview(print_url)
        except Exception as e:
            import traceback
            error_msg = str(e)
            traceback.print_exc()
            return _error(
                "pdf_generation_failed",
                f"Não foi possível gerar o PDF agora: {error_msg}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        safe_name = _safe_filename(resume.name or resume.target_position or "Curriculo")
        filename = f"Curriculo_{safe_name}_{date.today().isoformat()}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

