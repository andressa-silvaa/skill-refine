"""
Payload builders for analysis API responses.
Stable contract: same shape for run (202), latest (200), and history items.
i18n: insights use canonical keys (key + params); frontend translates via t(key, params).
"""
from __future__ import annotations

from typing import Any

from apps.analysis.models import ResumeAnalysis


def _normalize_strength(s: dict | str) -> dict[str, Any]:
    """Normalize to { key, params? }. Accepts legacy { title, description } for backward compat."""
    if isinstance(s, str):
        return {"key": "analysis.insights.strengths.other", "params": {}}
    key = s.get("key")
    if key:
        return {"key": key, "params": s.get("params") or {}}
    # Legacy: title/description -> synthesize key for backward compat (front can still have key for "other")
    return {"key": "analysis.insights.strengths.other", "params": {"title": s.get("title") or ""}}


def _normalize_improvement(i: dict | str) -> dict[str, Any]:
    """Normalize to { key, priority?, params? }. Accepts legacy { title, priority, description }."""
    if isinstance(i, str):
        return {"key": "analysis.insights.improvements.other", "priority": "medium", "params": {}}
    key = i.get("key")
    if key:
        out = {"key": key, "params": i.get("params") or {}}
        if i.get("priority") in ("high", "medium", "low"):
            out["priority"] = i["priority"]
        return out
    return {
        "key": "analysis.insights.improvements.other",
        "priority": i.get("priority") if i.get("priority") in ("high", "medium", "low") else "medium",
        "params": {"title": i.get("title") or ""},
    }


def analysis_payload(analysis: ResumeAnalysis) -> dict[str, Any]:
    """Build the stable API response. Insights use canonical keys (key + params) for frontend i18n."""
    task_scores = analysis.task_scores or {}
    payload_json = analysis.payload_json or {}
    insights = payload_json.get("insights") or {}
    strengths = insights.get("strengths") or []
    improvements = insights.get("improvements") or []
    recommendations = payload_json.get("recommendations") or []

    out: dict[str, Any] = {
        "id": str(analysis.id),
        "resumeId": str(analysis.resume_id),
        "status": analysis.status,
        "score": analysis.score,
        "taskScores": {
            "ats": task_scores.get("ats"),
            "clarity": task_scores.get("clarity"),
            "seniority": task_scores.get("seniority"),
            "matching": task_scores.get("matching"),
        },
        "insights": {
            "strengths": [_normalize_strength(s) for s in strengths],
            "improvements": [_normalize_improvement(i) for i in improvements],
        },
        "recommendations": recommendations,
        "metadata": {
            "modelName": analysis.model_name or "",
            "modelVersion": analysis.model_version or "",
            "provider": analysis.provider or "local",
        },
        "createdAt": analysis.created_at.isoformat(),
        "updatedAt": analysis.updated_at.isoformat(),
    }
    if analysis.status == "failed" and analysis.error_message:
        out["errorMessage"] = analysis.error_message
    return out
