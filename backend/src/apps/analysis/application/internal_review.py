"""
Query helpers and serialization for internal (token-gated) analysis review endpoints.
No resume text; identifiers are pseudo-keys (hashed), not raw UUIDs.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Mapping

from django.conf import settings
from django.db.models import Q, QuerySet
from django.http import HttpRequest

from apps.analysis.models import AnalysisStatus, ResumeAnalysis

logger = logging.getLogger(__name__)


def resolve_review_hash_salt() -> str:
    explicit = (getattr(settings, "ANALYSIS_INTERNAL_REVIEW_KEY_SALT", None) or "").strip()
    if explicit:
        return explicit
    sk = getattr(settings, "SECRET_KEY", "") or ""
    return sk[:48] if sk else "skill-refine-fallback-salt"


def pseudo_key(*, raw_id: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{raw_id}".encode("utf-8")).hexdigest()[:32]


def _parse_int(v: str | None, default: int | None) -> int | None:
    if v is None or v == "":
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _parse_since(v: str | None) -> datetime | None:
    if not v or not str(v).strip():
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None


def base_done_queryset() -> QuerySet[ResumeAnalysis]:
    return ResumeAnalysis.objects.filter(status=AnalysisStatus.DONE).order_by("-created_at")


def _get_param(params: Mapping[str, Any], key: str) -> str | None:
    if hasattr(params, "get"):
        v = params.get(key)
        return str(v) if v is not None else None
    return None


def _query_params(params: Any) -> Mapping[str, Any]:
    """DRF Request has ``query_params``; Django WSGIRequest has ``GET``; dict is accepted as-is."""
    qp = getattr(params, "query_params", None)
    if qp is not None:
        return qp
    if isinstance(params, HttpRequest):
        return params.GET
    return params


def apply_internal_review_filters(
    qs: QuerySet[ResumeAnalysis],
    params: Mapping[str, Any] | Any,
    *,
    confidence: str,
) -> QuerySet[ResumeAnalysis]:
    qp = _query_params(params)

    qs = qs.filter(
        Q(seniority_confidence=confidence)
        | (Q(seniority_confidence="") & Q(payload_json__seniorityConfidence=confidence))
    )

    since = _parse_since(_get_param(qp, "since"))
    if since is not None:
        qs = qs.filter(created_at__gte=since)

    smin = _parse_int(_get_param(qp, "score_min"), None)
    smax = _parse_int(_get_param(qp, "score_max"), None)
    if smin is not None:
        qs = qs.filter(score__gte=smin)
    if smax is not None:
        qs = qs.filter(score__lte=smax)

    cmin = _parse_int(_get_param(qp, "min_completeness"), None)
    cmax = _parse_int(_get_param(qp, "max_completeness"), None)
    if cmin is not None:
        qs = qs.filter(payload_json__completeness__score__gte=cmin)
    if cmax is not None:
        qs = qs.filter(payload_json__completeness__score__lte=cmax)

    label = (_get_param(qp, "seniority_label") or "").strip()
    if label:
        qs = qs.filter(
            Q(seniority_final_label=label)
            | (Q(seniority_final_label="") & Q(payload_json__seniorityClass=label))
        )

    return qs


def resolve_analysis_by_pseudo_key(analysis_key: str, *, salt: str) -> ResumeAnalysis | None:
    """
    Map opaque analysisKey (from low-confidence list) back to ResumeAnalysis.
    O(n) over DONE rows — acceptable for internal review volumes.
    """
    key = (analysis_key or "").strip().lower()
    if len(key) != 32:
        return None
    qs = ResumeAnalysis.objects.filter(status=AnalysisStatus.DONE).values_list("id", flat=True)
    for pk in qs.iterator(chunk_size=500):
        if pseudo_key(raw_id=str(pk), salt=salt) == key:
            return ResumeAnalysis.objects.filter(pk=pk).first()
    return None


def filter_queryset_by_gating_reason(
    qs: QuerySet[ResumeAnalysis],
    code: str,
    *,
    prefetch_limit: int = 5000,
) -> list[ResumeAnalysis]:
    """
    Keep rows whose ``payload_json.gatingReasons`` contains ``code`` (exact string).

    PostgreSQL uses a JSON containment query; SQLite / others scan up to ``prefetch_limit`` rows
    (internal endpoint only; bounded work).
    """
    from django.db import connection

    if connection.vendor == "postgresql":
        return list(qs.filter(payload_json__gatingReasons__contains=[code])[:prefetch_limit])

    out: list[ResumeAnalysis] = []
    for a in qs[:prefetch_limit].iterator(chunk_size=200):
        gr = (a.payload_json or {}).get("gatingReasons") or []
        if isinstance(gr, list) and code in gr:
            out.append(a)
    return out


def serialize_review_item(analysis: ResumeAnalysis, *, salt: str) -> dict[str, Any]:
    pj = analysis.payload_json or {}
    completeness = pj.get("completeness") if isinstance(pj.get("completeness"), dict) else {}
    conf = (analysis.seniority_confidence or "").strip() or (pj.get("seniorityConfidence") or "")
    rule = (analysis.seniority_rule_label or "").strip() or (pj.get("seniorityRuleBase") or "")
    display = (pj.get("seniorityClass") or "").strip() or (analysis.seniority_final_label or "").strip()
    return {
        "analysisKey": pseudo_key(raw_id=str(analysis.id), salt=salt),
        "resumeKey": pseudo_key(raw_id=str(analysis.resume_id), salt=salt),
        "userKey": pseudo_key(raw_id=str(analysis.user_id), salt=salt),
        "createdAt": analysis.created_at.isoformat(),
        "score": analysis.score,
        "seniorityLabel": display,
        "seniorityFinalLabel": (analysis.seniority_final_label or "").strip(),
        "seniorityLabelSource": (analysis.seniority_label_source or "").strip(),
        "seniorityReviewLabel": (analysis.seniority_review_label or "").strip(),
        "seniorityConfidence": conf,
        "seniorityRuleBase": rule,
        "seniorityMlStatus": pj.get("seniorityMlStatus") or "",
        "insufficientData": bool(pj.get("insufficientData")),
        "gatingReasons": list(pj.get("gatingReasons") or [])
        if isinstance(pj.get("gatingReasons"), list)
        else [],
        "completenessScore": completeness.get("score"),
        "completenessLevel": completeness.get("level"),
        "modelVersion": analysis.model_version or "",
        "provider": analysis.provider or "",
        "policyVersion": (analysis.seniority_policy_version or "").strip(),
    }


def log_internal_review_access(
    *,
    request: HttpRequest,
    confidence: str | None,
    result_count: int,
    endpoint: str,
) -> None:
    extra: dict[str, Any] = {
        "event": "internal_analysis_review",
        "endpoint": endpoint,
        "result_count": result_count,
        "client_ip": request.META.get("REMOTE_ADDR"),
    }
    if confidence:
        extra["confidence"] = confidence
    logger.info("internal_analysis_review_access", extra=extra)
