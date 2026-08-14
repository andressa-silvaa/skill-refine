"""
Internal review API: low-confidence seniority cases (pseudo-keys only, no resume text).
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import timedelta

from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.application.dataset_export import build_seniority_dataset_record
from apps.analysis.application.internal_review import (
    apply_internal_review_filters,
    base_done_queryset,
    filter_queryset_by_gating_reason,
    log_internal_review_access,
    resolve_analysis_by_pseudo_key,
    resolve_review_hash_salt,
    serialize_review_item,
)
from apps.analysis.application.seniority_persist import (
    SENIORITY_LABEL_TO_SCORE,
    normalize_seniority_label,
)
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.audit.infrastructure.logger import OrmAuditLogger

from .internal_permissions import HasAnalysisInternalReviewSecret

from .internal_seniority_views import SeniorityInternalMetricsView, SeniorityReviewSubmitView


logger = logging.getLogger(__name__)

_PREFETCH = (
    "resume__resumecontact",
    "resume__resumeexperience_set__resumeexperiencebullet_set",
    "resume__resumeeducation_set",
    "resume__resumeskill_set",
    "resume__resumelanguage_set",
)


def _parse_limit(request, default: int = 50, cap: int = 200) -> int:
    raw = request.query_params.get("limit", str(default))
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = default
    return max(1, min(n, cap))


def _confidence_param(request) -> str:
    conf = (request.query_params.get("confidence") or "low").strip().lower()
    if conf not in ("low", "medium", "high"):
        return "low"
    return conf


def _resolve_analyses_for_internal(
    request,
    *,
    confidence: str,
    limit: int,
) -> list[ResumeAnalysis]:
    base = base_done_queryset().select_related("resume", "user").prefetch_related(*_PREFETCH)
    qs = apply_internal_review_filters(base, request, confidence=confidence)
    has_reason = (request.query_params.get("has_reason") or "").strip()
    if has_reason:
        matched = filter_queryset_by_gating_reason(qs, has_reason)
        return matched[:limit]
    return list(qs[:limit])


class LowConfidenceAnalysisReviewView(APIView):
    """
    GET /analysis/internal/low-confidence

    Filters: confidence, limit, since, score_min, score_max, min_completeness, max_completeness,
    seniority_label, has_reason (exact gating reason code, e.g. no_experiences).
    """

    authentication_classes = []
    permission_classes = [HasAnalysisInternalReviewSecret]
    throttle_scope = "analysis_internal"

    def get(self, request):
        conf = _confidence_param(request)
        limit = _parse_limit(request)
        salt = resolve_review_hash_salt()

        analyses = _resolve_analyses_for_internal(request, confidence=conf, limit=limit)
        items = [serialize_review_item(a, salt=salt) for a in analyses]

        log_internal_review_access(
            request=request,
            confidence=conf,
            result_count=len(items),
            endpoint="low-confidence",
        )
        try:
            OrmAuditLogger().log(
                action="analysis.internal.low_confidence_list",
                actor_user_id=None,
                subject_user_id=None,
                ip=request.META.get("REMOTE_ADDR"),
                user_agent=request.headers.get("User-Agent"),
                metadata={
                    "confidence": conf,
                    "result_count": len(items),
                    "has_reason": (request.query_params.get("has_reason") or "").strip() or None,
                },
            )
        except Exception:
            logger.exception("audit log failed (ignored)")

        return Response({"confidence": conf, "count": len(items), "items": items})


class LowConfidenceAnalysisExportView(APIView):
    """
    GET /analysis/internal/low-confidence/export

    Same filters as the list endpoint; response is JSONL (signals-only; no text_sanitized).
    """

    authentication_classes = []
    permission_classes = [HasAnalysisInternalReviewSecret]
    throttle_scope = "analysis_internal"

    def get(self, request):
        conf = _confidence_param(request)
        limit = _parse_limit(request, default=200, cap=2000)
        salt = resolve_review_hash_salt()

        analyses = _resolve_analyses_for_internal(request, confidence=conf, limit=limit)

        log_internal_review_access(
            request=request,
            confidence=conf,
            result_count=len(analyses),
            endpoint="low-confidence/export",
        )
        try:
            OrmAuditLogger().log(
                action="analysis.internal.low_confidence_export",
                actor_user_id=None,
                subject_user_id=None,
                ip=request.META.get("REMOTE_ADDR"),
                user_agent=request.headers.get("User-Agent"),
                metadata={"confidence": conf, "row_count": len(analyses), "format": "jsonl"},
            )
        except Exception:
            logger.exception("audit log failed (ignored)")

        def line_iter():
            for a in analyses:
                row = build_seniority_dataset_record(a, hash_salt=salt, include_text=False)
                yield json.dumps(row, ensure_ascii=False) + "\n"

        resp = StreamingHttpResponse(line_iter(), content_type="application/x-ndjson; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="low_confidence_dataset.jsonl"'
        return resp
