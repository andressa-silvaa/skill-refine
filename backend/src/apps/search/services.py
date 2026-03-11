"""
Global search: resumes, analyses, versions.
Returns unified items with type, title, subtitle, url.
"""
from __future__ import annotations

from django.db.models import Q

from apps.analysis.models import ResumeAnalysis
from apps.resumes.infrastructure.models import Resume, ResumeVersion


def search_resumes(user_id: str, q: str, limit: int) -> list[dict]:
    q_clean = (q or "").strip()
    if not q_clean:
        return []
    qs = (
        Resume.objects.filter(user_id=user_id, deleted_at__isnull=True)
        .filter(
            Q(name__icontains=q_clean)
            | Q(target_position__icontains=q_clean)
            | Q(summary__icontains=q_clean)
        )
        .order_by("-updated_at")[:limit]
    )
    return [
        {
            "type": "resume",
            "id": str(r.id),
            "title": r.name or r.target_position or "Currículo",
            "subtitle": (r.target_position or "")[:60] if r.target_position else "",
            "url": f"/protected/resumes?editResumeId={r.id}",
        }
        for r in qs
    ]


def search_analyses(user_id: str, q: str, limit: int) -> list[dict]:
    q_clean = (q or "").strip()
    if not q_clean:
        return []
    qs = (
        ResumeAnalysis.objects.filter(user_id=user_id)
        .select_related("resume")
        .filter(
            Q(resume__name__icontains=q_clean)
            | Q(resume__target_position__icontains=q_clean)
        )
        .order_by("-created_at")[:limit]
    )
    return [
        {
            "type": "analysis",
            "id": str(a.id),
            "title": (a.resume.name or a.resume.target_position or "Análise")[:80],
            "subtitle": f"Score: {a.score}" if a.score is not None else "",
            "url": f"/protected/ai-analysis?resumeId={a.resume_id}",
        }
        for a in qs
    ]


def search_versions(user_id: str, q: str, limit: int) -> list[dict]:
    q_clean = (q or "").strip()
    if not q_clean:
        return []
    qs = (
        ResumeVersion.objects.filter(user_id=user_id)
        .select_related("resume")
        .filter(
            Q(resume__name__icontains=q_clean)
            | Q(resume__target_position__icontains=q_clean)
        )
        .order_by("-created_at")[:limit]
    )
    return [
        {
            "type": "version",
            "id": str(v.id),
            "title": (v.resume.name or v.resume.target_position or "Versão")[:80],
            "subtitle": f"v{v.version_number}",
            "url": f"/protected/version-history",
        }
        for v in qs
    ]


def global_search(
    user_id: str,
    q: str,
    types: list[str] | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Search across resumes, analyses, versions.
    types: ["resume", "analysis", "version"] or None for all.
    """
    q_clean = (q or "").strip()
    if not q_clean:
        return []
    allowed = {"resume", "analysis", "version"}
    requested = set(types or allowed) & allowed
    per_type = max(5, limit // len(requested)) if requested else limit
    items: list[dict] = []
    if "resume" in requested:
        items.extend(search_resumes(user_id, q_clean, per_type))
    if "analysis" in requested:
        items.extend(search_analyses(user_id, q_clean, per_type))
    if "version" in requested:
        items.extend(search_versions(user_id, q_clean, per_type))
    return items[:limit]
