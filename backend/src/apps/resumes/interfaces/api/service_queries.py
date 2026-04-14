from __future__ import annotations

from typing import Any

from django.db.models import F, OuterRef, Prefetch, Q, QuerySet, Subquery
from django.db.models.functions import Coalesce

from apps.analysis.application.analysis_resume_validity import valid_resume_analysis_q
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume, ResumeSkill, ResumeTag

from .payloads import resume_detail_prefetch

ResumeListFilters = dict[str, Any]


def _list_resumes_queryset(user_id: str):
    """Base queryset for list resumes (same ordering and prefetch as list_resumes)."""
    return (
        Resume.objects.filter(user_id=user_id, deleted_at__isnull=True)
        .prefetch_related(
            Prefetch(
                "resumetag_set",
                queryset=ResumeTag.objects.order_by("position_index"),
            ),
            Prefetch(
                "resumeskill_set",
                queryset=ResumeSkill.objects.order_by("position_index"),
            ),
        )
    )


def _apply_list_filters(qs: QuerySet[Resume], filters: ResumeListFilters | None):
    data = filters or {}

    status_value = data.get("status")
    if status_value:
        qs = qs.filter(status=status_value)

    search = (data.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(name__icontains=search) | Q(target_position__icontains=search) | Q(summary__icontains=search)
        )

    score_min = data.get("score_min")
    score_max = data.get("score_max")
    include_no_score = bool(data.get("include_no_score"))
    needs_effective_score = (
        include_no_score
        or score_min is not None
        or score_max is not None
        or (data.get("sort") == "score")
    )
    if needs_effective_score:
        latest_analysis_score_subquery = (
            ResumeAnalysis.objects.filter(
                user_id=OuterRef("user_id"),
                resume_id=OuterRef("id"),
                status=AnalysisStatus.DONE,
                score__isnull=False,
            )
            .filter(valid_resume_analysis_q())
            .order_by("-created_at")
            .values("score")[:1]
        )
        qs = qs.annotate(
            latest_analysis_score=Subquery(latest_analysis_score_subquery),
            effective_score=Coalesce("latest_analysis_score", "score"),
        )

    if include_no_score:
        qs = qs.filter(effective_score__isnull=True)
    else:
        if score_min is not None:
            qs = qs.filter(effective_score__gte=score_min)
        if score_max is not None:
            qs = qs.filter(effective_score__lte=score_max)

    updated_from = data.get("updated_from")
    if updated_from:
        qs = qs.filter(updated_at__date__gte=updated_from)
    updated_to = data.get("updated_to")
    if updated_to:
        qs = qs.filter(updated_at__date__lte=updated_to)

    sort = data.get("sort") or "recent"
    if sort == "oldest":
        qs = qs.order_by("updated_at")
    elif sort == "score":
        qs = qs.order_by(F("effective_score").desc(nulls_last=True), "-updated_at")
    elif sort == "name":
        qs = qs.order_by("name", "-updated_at")
    else:
        qs = qs.order_by("-updated_at")
    return qs


def list_resumes(user_id: str, filters: ResumeListFilters | None = None):
    """Return queryset of user resumes with list prefetch (tags, skills)."""
    return _apply_list_filters(_list_resumes_queryset(user_id), filters)


def list_resumes_paginated(
    user_id: str, limit: int, offset: int, filters: ResumeListFilters | None = None
) -> tuple[list[Resume], int]:
    """
    Return (page of resumes, total count) for the user.
    Same ordering (-updated_at) and prefetch as list_resumes.
    """
    qs = _apply_list_filters(_list_resumes_queryset(user_id), filters)
    total = qs.count()
    page = list(qs[offset : offset + limit])
    return (page, total)


def get_resume_for_edit(user_id: str, resume_id: str) -> Resume | None:
    """Return resume for GET draft/detail or None if not found."""
    return (
        Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True)
        .select_related("resumecontact")
        .prefetch_related(*resume_detail_prefetch())
        .first()
    )


def get_resume_for_pdf_data(resume_id: str, user_id: str) -> Resume | None:
    """Return resume with detail prefetch for PDF data endpoint (token-validated)."""
    return (
        Resume.objects.filter(
            id=resume_id,
            user_id=user_id,
            deleted_at__isnull=True,
        )
        .select_related("resumecontact")
        .prefetch_related(*resume_detail_prefetch())
        .first()
    )


def get_resume_by_id_and_user(user_id: str, resume_id: str) -> Resume | None:
    """Return resume by id and user (no prefetch). Used for PDF token and PDF download."""
    return Resume.objects.filter(
        id=resume_id, user_id=user_id, deleted_at__isnull=True
    ).first()
