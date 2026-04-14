"""
Payload builders for analysis API responses.
Stable contract: same shape for run (202), latest (200), and history items.
i18n: insights use canonical keys (key + params); frontend translates via t(key, params).
"""
from __future__ import annotations

from typing import Any

from django.conf import settings

from apps.analysis.models import ResumeAnalysis

# Generic placeholder; never surface to clients (no actionable meaning).
_STRENGTH_KEY_OMIT = frozenset({"analysis.insights.strengths.other"})
_VALID_SENIORITY = frozenset({"intern", "junior", "mid", "senior"})


def _normalize_task_models(task_models: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for task, meta in (task_models or {}).items():
        if not isinstance(meta, dict):
            continue
        out[str(task)] = {
            "modelName": meta.get("modelName") or "",
            "modelVersion": meta.get("modelVersion") or "",
            "datasetVersion": meta.get("datasetVersion") or "",
            "provider": meta.get("provider") or "local",
        }
    return out


def _normalize_strength(s: dict | str) -> dict[str, Any]:
    """Normalize to { key, params?, evidence? }. Accepts legacy { title, description } for backward compat."""
    if isinstance(s, str):
        return {"key": "analysis.insights.strengths.other", "params": {}}
    key = s.get("key")
    if key:
        if not str(key).startswith("analysis.insights.strengths."):
            key = "analysis.insights.strengths.other"
        out = {"key": key, "params": s.get("params") or {}}
        if isinstance(s.get("evidence"), dict):
            out["evidence"] = s["evidence"]
        return out
    # Legacy: title/description -> synthesize key for backward compat (front can still have key for "other")
    return {"key": "analysis.insights.strengths.other", "params": {"title": s.get("title") or ""}}


def _normalize_improvement(i: dict | str) -> dict[str, Any]:
    """Normalize to { key, priority?, params? }. Accepts legacy { title, priority, description }."""
    if isinstance(i, str):
        return {"key": "analysis.insights.improvements.other", "priority": "medium", "params": {}}
    key = i.get("key")
    if key:
        if not str(key).startswith("analysis.insights.improvements."):
            key = "analysis.insights.improvements.other"
        out = {"key": key, "params": i.get("params") or {}}
        if i.get("priority") in ("high", "medium", "low"):
            out["priority"] = i["priority"]
        if isinstance(i.get("evidence"), dict):
            out["evidence"] = i["evidence"]
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

    completeness = payload_json.get("completeness")
    if isinstance(completeness, dict):
        completeness_out = {
            "score": completeness.get("score"),
            "level": completeness.get("level"),
            "confidence": completeness.get("confidence"),
        }
    else:
        completeness_out = None

    seniority_class = payload_json.get("seniorityClass")
    seniority_confidence = payload_json.get("seniorityConfidence")
    if seniority_confidence not in ("low", "medium", "high"):
        db_conf = (getattr(analysis, "seniority_confidence", None) or "").strip()
        if db_conf in ("low", "medium", "high"):
            seniority_confidence = db_conf
    score_meaning = payload_json.get("scoreMeaning")
    insufficient_data = payload_json.get("insufficientData")
    gating_reasons = payload_json.get("gatingReasons")

    out: dict[str, Any] = {
        "id": str(analysis.id),
        "resumeId": str(analysis.resume_id),
        "status": analysis.status,
        "score": analysis.score,
        "completeness": completeness_out,
        "taskScores": {
            "ats": task_scores.get("ats"),
            "clarity": task_scores.get("clarity"),
            "seniority": task_scores.get("seniority"),
            "matching": task_scores.get("matching"),
            "targetFit": task_scores.get("target_fit"),
            "targetSeniority": task_scores.get("target_seniority"),
        },
        "insights": {
            "strengths": [
                s for s in (_normalize_strength(x) for x in strengths) if s["key"] not in _STRENGTH_KEY_OMIT
            ],
            "improvements": [_normalize_improvement(i) for i in improvements],
        },
        "recommendations": recommendations,
        "metadata": {
            "modelName": analysis.model_name or "",
            "modelVersion": analysis.model_version or "",
            "datasetVersion": analysis.dataset_version or "",
            "provider": analysis.provider or "local",
            "taskModels": _normalize_task_models(payload_json.get("model_metadata_by_task")),
        },
        "createdAt": analysis.created_at.isoformat(),
        "updatedAt": analysis.updated_at.isoformat(),
    }
    lab = (seniority_class if isinstance(seniority_class, str) else "") or ""
    lab = lab.strip().lower()
    if lab not in _VALID_SENIORITY:
        lab = (str(getattr(analysis, "seniority_final_label", "") or "").strip().lower())
    if lab not in _VALID_SENIORITY:
        lab = (str(getattr(analysis, "seniority_rule_label", "") or "").strip().lower())
    if lab not in _VALID_SENIORITY:
        lab = "junior"
    out["seniorityLabel"] = lab
    if seniority_confidence in ("low", "medium", "high"):
        out["seniorityConfidence"] = seniority_confidence
    if isinstance(score_meaning, str) and score_meaning:
        out["scoreMeaning"] = score_meaning
    if isinstance(insufficient_data, bool):
        out["insufficientData"] = insufficient_data
    if isinstance(gating_reasons, list):
        out["gatingReasons"] = gating_reasons

    tf = payload_json.get("targetFitScore")
    if isinstance(tf, (int, float)):
        out["targetFitScore"] = int(tf)
    tsl = payload_json.get("targetSeniorityLabel")
    if isinstance(tsl, str) and tsl.strip().lower() in _VALID_SENIORITY:
        out["targetSeniorityLabel"] = tsl.strip().lower()
    trd = payload_json.get("targetRoleDomain")
    if isinstance(trd, dict):
        out["targetRoleDomain"] = {
            "category": str(trd.get("category") or ""),
            "confidence": str(trd.get("confidence") or "low"),
            "evidenceTokens": list(trd.get("evidenceTokens") or [])[:8],
        }
    rd = payload_json.get("resumeDomain")
    if isinstance(rd, dict):
        out["resumeDomain"] = {
            "category": str(rd.get("category") or ""),
            "confidence": str(rd.get("confidence") or "low"),
            "evidenceTokens": list(rd.get("evidenceTokens") or [])[:8],
        }
    ev = payload_json.get("targetFitEvidence")
    if isinstance(ev, dict):
        tfe_out: dict[str, Any] = {
            "matchedTerms": list(ev.get("matchedTerms") or [])[:20],
            "missingTerms": list(ev.get("missingTerms") or [])[:20],
            "matchedSkills": list(ev.get("matchedSkills") or [])[:20],
            "experienceKeywordHits": ev.get("experienceKeywordHits"),
            "educationAlignment": str(ev.get("educationAlignment") or ""),
            "portfolioEvidence": bool(ev.get("portfolioEvidence")),
            "requiredTermsHit": ev.get("requiredTermsHit"),
            "requiredTermsTotal": ev.get("requiredTermsTotal"),
            "skillsHit": ev.get("skillsHit"),
        }
        sem = ev.get("semanticEvidence")
        if isinstance(sem, dict):
            kws = sem.get("keywords") or []
            if isinstance(kws, list):
                tfe_out["semanticEvidence"] = {
                    "keywords": [str(x) for x in kws if isinstance(x, str) and x.strip()][:12],
                }
        out["targetFitEvidence"] = tfe_out
    cs = payload_json.get("careerSwitch")
    if isinstance(cs, dict):
        out["careerSwitch"] = {
            "detected": bool(cs.get("detected")),
            "reasonKey": str(cs.get("reasonKey") or ""),
        }
    clamp = payload_json.get("targetSeniorityClampReasons")
    if isinstance(clamp, list):
        out["targetSeniorityClampReasons"] = [str(x) for x in clamp if isinstance(x, str)]

    tfp = payload_json.get("targetFitProvider")
    if isinstance(tfp, str) and tfp.strip():
        out["targetFitProvider"] = tfp.strip()
    tfmv = payload_json.get("targetFitModelVersion")
    if isinstance(tfmv, str):
        out["targetFitModelVersion"] = tfmv
    tfdv = payload_json.get("targetFitDatasetVersion")
    if isinstance(tfdv, str):
        out["targetFitDatasetVersion"] = tfdv

    if getattr(settings, "DEBUG", False):
        dbg = payload_json.get("debug")
        if isinstance(dbg, dict):
            out["debug"] = dbg

    if analysis.status == "failed" and analysis.error_message:
        out["errorMessage"] = analysis.error_message
    return out
