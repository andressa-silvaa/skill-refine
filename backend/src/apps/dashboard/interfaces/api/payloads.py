from __future__ import annotations

from typing import Any


def summary_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "totalResumes": int(data.get("totalResumes") or 0),
        "completeResumes": int(data.get("completeResumes") or 0),
        "draftResumes": int(data.get("draftResumes") or 0),
        "lastAnalysisAt": data.get("lastAnalysisAt"),
        "lastAnalyzedResumeId": data.get("lastAnalyzedResumeId"),
        "lastAnalyzedResumeTitle": data.get("lastAnalyzedResumeTitle"),
        "averageScore": data.get("averageScore"),
        "averageScoreDelta": data.get("averageScoreDelta"),
        "pendingSuggestions": int(data.get("pendingSuggestions") or 0),
        "highPrioritySuggestions": int(data.get("highPrioritySuggestions") or 0),
    }


def score_point_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "period": item.get("period") or "",
        "score": int(item.get("score") or 0),
    }


def competency_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": item.get("key") or "",
        "value": int(item.get("value") or 0),
    }


def recent_resume_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id") or "",
        "name": item.get("name") or "",
        "updatedAt": item.get("updatedAt"),
        "status": item.get("status") or "draft",
        "score": item.get("score"),
    }


def insight_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id") or "",
        "key": item.get("key") or "analysis.insights.improvements.other",
        "priority": item.get("priority") or "medium",
        "count": int(item.get("count") or 0),
        "resumeId": item.get("resumeId"),
        "resumeTitle": item.get("resumeTitle"),
        "analysisId": item.get("analysisId"),
        "createdAt": item.get("createdAt"),
        "params": item.get("params") or {},
    }


def dashboard_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": summary_payload(data.get("summary") or {}),
        "scoreEvolution": [score_point_payload(i) for i in (data.get("scoreEvolution") or [])],
        "competencies": [competency_payload(i) for i in (data.get("competencies") or [])],
        "recentResumes": [recent_resume_payload(i) for i in (data.get("recentResumes") or [])],
        "aiInsights": [insight_payload(i) for i in (data.get("aiInsights") or [])],
    }

