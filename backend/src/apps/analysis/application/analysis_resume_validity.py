"""
Decide if a stored ResumeAnalysis still matches the current resume snapshot.
After any resume edit, older analyses must not be shown as "latest" until a new run.
"""
from __future__ import annotations

from django.db.models import OuterRef, Q

from apps.analysis.models import AnalysisStatus, ResumeAnalysis


def is_analysis_valid_for_resume(resume, analysis: ResumeAnalysis) -> bool:
    """
    True if the resume has not changed since this analysis run was tied to it.

    When resume_content_synced_at is set (all new runs), require exact match with resume.updated_at.
    Legacy rows (null): fall back to timestamp heuristics.
    """
    synced = getattr(analysis, "resume_content_synced_at", None)
    if synced is not None:
        return resume.updated_at == synced

    r_ts = resume.updated_at
    if analysis.status in (AnalysisStatus.DONE, AnalysisStatus.FAILED):
        return r_ts <= analysis.updated_at
    if analysis.status in (AnalysisStatus.PENDING, AnalysisStatus.RUNNING):
        return r_ts <= analysis.created_at
    return False


def valid_resume_analysis_q() -> Q:
    """
    For Subquery/Filter on ResumeAnalysis where OuterRef is a Resume row (updated_at, id, user_id).
    """
    return (
        Q(resume_content_synced_at=OuterRef("updated_at"))
        | Q(
            resume_content_synced_at__isnull=True,
            status__in=(AnalysisStatus.DONE, AnalysisStatus.FAILED),
            updated_at__gte=OuterRef("updated_at"),
        )
        | Q(
            resume_content_synced_at__isnull=True,
            status__in=(AnalysisStatus.PENDING, AnalysisStatus.RUNNING),
            created_at__gte=OuterRef("updated_at"),
        )
    )
