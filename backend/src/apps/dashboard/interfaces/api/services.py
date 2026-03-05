from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from statistics import mean
from typing import Any

from django.db.models import Avg, OuterRef, Q, Subquery
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume, ResumeStatus


def _round_int(value: float | int | None, fallback: int | None = None) -> int | None:
    if value is None:
        return fallback
    return int(round(float(value)))


def _clamp_score(value: int | float | None, fallback: int = 0) -> int:
    parsed = _round_int(value, fallback=fallback)
    if parsed is None:
        return fallback
    return max(0, min(100, parsed))


def _extract_improvements(analysis: ResumeAnalysis) -> list[dict[str, Any]]:
    payload = analysis.payload_json or {}
    insights = payload.get("insights") if isinstance(payload, dict) else {}
    improvements = insights.get("improvements") if isinstance(insights, dict) else []
    if not isinstance(improvements, list):
        return []
    return [i for i in improvements if isinstance(i, dict)]


def _latest_done_analyses_by_resume(user_id: str) -> list[ResumeAnalysis]:
    latest_analysis_subquery = (
        ResumeAnalysis.objects.filter(
            user_id=user_id,
            status=AnalysisStatus.DONE,
            resume_id=OuterRef("resume_id"),
        )
        .order_by("-created_at")
        .values("id")[:1]
    )
    return list(
        ResumeAnalysis.objects.filter(user_id=user_id, status=AnalysisStatus.DONE)
        .filter(id=Subquery(latest_analysis_subquery))
        .select_related("resume")
    )


def _build_competencies(
    latest_done_analyses: list[ResumeAnalysis],
    total_resumes: int,
    complete_resumes: int,
) -> list[dict[str, Any]]:
    ats_scores: list[int] = []
    clarity_scores: list[int] = []
    hard_scores: list[int] = []
    soft_scores: list[int] = []

    ats_keyword_suggestions = 0

    for analysis in latest_done_analyses:
        task_scores = analysis.task_scores or {}
        ats = task_scores.get("ats")
        clarity = task_scores.get("clarity")
        matching = task_scores.get("matching")
        seniority = task_scores.get("seniority")

        if isinstance(ats, (int, float)):
            ats_scores.append(int(ats))
        if isinstance(clarity, (int, float)):
            clarity_scores.append(int(clarity))

        if isinstance(matching, (int, float)):
            hard_scores.append(int(matching))
        elif isinstance(ats, (int, float)):
            hard_scores.append(int(ats))

        if isinstance(clarity, (int, float)) and isinstance(seniority, (int, float)):
            soft_scores.append(int(round((float(clarity) + float(seniority)) / 2)))
        elif isinstance(clarity, (int, float)):
            soft_scores.append(int(clarity))
        elif isinstance(seniority, (int, float)):
            soft_scores.append(int(seniority))

        improvements = _extract_improvements(analysis)
        has_ats_keyword_suggestion = any(
            str(item.get("key") or "").strip() == "analysis.insights.improvements.ats_keywords"
            for item in improvements
        )
        if has_ats_keyword_suggestion:
            ats_keyword_suggestions += 1

    format_score = 0
    if total_resumes > 0:
        format_score = _clamp_score((complete_resumes / total_resumes) * 100)

    keywords_score = 0
    if latest_done_analyses:
        ratio = ats_keyword_suggestions / len(latest_done_analyses)
        keywords_score = _clamp_score(100 - (ratio * 45))

    return [
        {"key": "hardSkills", "value": _clamp_score(mean(hard_scores) if hard_scores else 0)},
        {"key": "softSkills", "value": _clamp_score(mean(soft_scores) if soft_scores else 0)},
        {"key": "clarity", "value": _clamp_score(mean(clarity_scores) if clarity_scores else 0)},
        {"key": "ats", "value": _clamp_score(mean(ats_scores) if ats_scores else 0)},
        {"key": "format", "value": format_score},
        {"key": "keywords", "value": keywords_score},
    ]


def _build_recurring_insights(latest_done_analyses: list[ResumeAnalysis]) -> list[dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "priority": "medium",
            "resumeId": None,
            "resumeTitle": None,
            "analysisId": None,
            "createdAt": None,
            "params": {},
        }
    )

    priority_order = {"high": 3, "medium": 2, "low": 1}

    for analysis in latest_done_analyses:
        for improvement in _extract_improvements(analysis):
            key = str(improvement.get("key") or "").strip()
            if not key:
                continue

            info = stats[key]
            info["count"] += 1

            priority = str(improvement.get("priority") or "medium").strip()
            if priority not in priority_order:
                priority = "medium"
            if priority_order.get(priority, 0) > priority_order.get(info["priority"], 0):
                info["priority"] = priority

            previous_created_at = info["createdAt"] or ""
            current_created_at = analysis.created_at.isoformat()
            if current_created_at >= previous_created_at:
                info["resumeId"] = str(analysis.resume_id)
                resume_name = analysis.resume.name or analysis.resume.target_position or "Novo Currículo"
                info["resumeTitle"] = resume_name
                info["analysisId"] = str(analysis.id)
                info["createdAt"] = current_created_at
                params = improvement.get("params")
                info["params"] = params if isinstance(params, dict) else {}

    result = [
        {
            "id": f"{key}:{value['analysisId'] or 'na'}",
            "key": key,
            "priority": value["priority"],
            "count": value["count"],
            "resumeId": value["resumeId"],
            "resumeTitle": value["resumeTitle"],
            "analysisId": value["analysisId"],
            "createdAt": value["createdAt"],
            "params": value["params"],
        }
        for key, value in stats.items()
    ]

    result.sort(
        key=lambda item: (
            -priority_order.get(str(item.get("priority") or "medium"), 0),
            -int(item.get("count") or 0),
            str(item.get("createdAt") or ""),
        )
    )
    return result[:5]


def get_dashboard_summary(user_id: str) -> dict[str, Any]:
    resumes_qs = Resume.objects.filter(user_id=user_id, deleted_at__isnull=True)
    total_resumes = resumes_qs.count()
    complete_resumes = resumes_qs.filter(status=ResumeStatus.COMPLETE).count()
    draft_resumes = resumes_qs.filter(status=ResumeStatus.DRAFT).count()

    done_analyses_qs = ResumeAnalysis.objects.filter(user_id=user_id, status=AnalysisStatus.DONE)

    latest_done_analysis = done_analyses_qs.select_related("resume").order_by("-created_at").first()
    latest_done_analyses = _latest_done_analyses_by_resume(user_id)

    analysis_scores = list(done_analyses_qs.exclude(score__isnull=True).values_list("score", flat=True))
    resume_scores = list(resumes_qs.exclude(score__isnull=True).values_list("score", flat=True))
    score_source = analysis_scores if analysis_scores else resume_scores
    average_score = _round_int(mean(score_source), fallback=None) if score_source else None

    now = timezone.now()
    current_from = now - timedelta(days=30)
    previous_from = now - timedelta(days=60)
    current_avg = done_analyses_qs.filter(created_at__gte=current_from).aggregate(v=Avg("score")).get("v")
    previous_avg = done_analyses_qs.filter(
        Q(created_at__gte=previous_from) & Q(created_at__lt=current_from)
    ).aggregate(v=Avg("score")).get("v")
    average_score_delta = None
    if current_avg is not None and previous_avg not in (None, 0):
        average_score_delta = _round_int(((float(current_avg) - float(previous_avg)) / float(previous_avg)) * 100)

    pending_suggestions = 0
    high_priority_suggestions = 0
    for analysis in latest_done_analyses:
        for item in _extract_improvements(analysis):
            pending_suggestions += 1
            if str(item.get("priority") or "").strip() == "high":
                high_priority_suggestions += 1

    monthly_score_qs = (
        done_analyses_qs.exclude(score__isnull=True)
        .filter(created_at__gte=now - timedelta(days=365))
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(avg_score=Avg("score"))
        .order_by("month")
    )
    score_evolution = [
        {
            "period": row["month"].strftime("%Y-%m") if row.get("month") else "",
            "score": _clamp_score(row.get("avg_score"), fallback=0),
        }
        for row in monthly_score_qs
    ][-6:]

    latest_done_analysis_subquery = (
        ResumeAnalysis.objects.filter(
            user_id=user_id,
            status=AnalysisStatus.DONE,
            resume_id=OuterRef("id"),
        )
        .order_by("-created_at")
        .values("score")[:1]
    )
    recent_resumes_qs = (
        resumes_qs.order_by("-updated_at")
        .annotate(latest_analysis_score=Subquery(latest_done_analysis_subquery))
        .values("id", "name", "target_position", "updated_at", "status", "score", "latest_analysis_score")[:5]
    )
    recent_resumes = []
    for item in recent_resumes_qs:
        display_name = item["name"] or item["target_position"] or "Novo Currículo"
        recent_resumes.append(
            {
                "id": str(item["id"]),
                "name": display_name,
                "updatedAt": item["updated_at"].isoformat() if item.get("updated_at") else None,
                "status": item["status"],
                "score": item.get("latest_analysis_score")
                if item.get("latest_analysis_score") is not None
                else item.get("score"),
            }
        )

    if latest_done_analysis:
        last_analyzed_resume_title = (
            latest_done_analysis.resume.name
            or latest_done_analysis.resume.target_position
            or "Novo Currículo"
        )
    else:
        last_analyzed_resume_title = None

    return {
        "summary": {
            "totalResumes": total_resumes,
            "completeResumes": complete_resumes,
            "draftResumes": draft_resumes,
            "lastAnalysisAt": latest_done_analysis.created_at.isoformat() if latest_done_analysis else None,
            "lastAnalyzedResumeId": str(latest_done_analysis.resume_id) if latest_done_analysis else None,
            "lastAnalyzedResumeTitle": last_analyzed_resume_title,
            "averageScore": average_score,
            "averageScoreDelta": average_score_delta,
            "pendingSuggestions": pending_suggestions,
            "highPrioritySuggestions": high_priority_suggestions,
        },
        "scoreEvolution": score_evolution,
        "competencies": _build_competencies(
            latest_done_analyses=latest_done_analyses,
            total_resumes=total_resumes,
            complete_resumes=complete_resumes,
        ),
        "recentResumes": recent_resumes,
        "aiInsights": _build_recurring_insights(latest_done_analyses),
    }

