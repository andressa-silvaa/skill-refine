"""
Endpoints internos de senioridade: metricas agregadas e submissao da revisao humana.

Separado de ``internal_views.py``, que fica com a fila de baixa confianca. Sao publicos diferentes:
aqui e o anotador, la e quem audita a fila.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

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

class SeniorityInternalMetricsView(APIView):
    """GET /analysis/internal/metrics/seniority — aggregates for governance (no PII)."""

    authentication_classes = []
    permission_classes = [HasAnalysisInternalReviewSecret]
    throttle_scope = "analysis_internal"

    def get(self, request):
        days_raw = request.query_params.get("days", "7")
        try:
            days = max(1, min(int(days_raw), 90))
        except (TypeError, ValueError):
            days = 7

        cutoff = timezone.now() - timedelta(days=days)
        rows = ResumeAnalysis.objects.filter(status=AnalysisStatus.DONE, created_at__gte=cutoff).values_list(
            "payload_json",
            flat=True,
        )

        by_conf: Counter[str] = Counter()
        reasons: Counter[str] = Counter()
        for pj in rows:
            data = pj or {}
            by_conf[str(data.get("seniorityConfidence") or "unknown")] += 1
            gr = data.get("gatingReasons") or []
            if isinstance(gr, list):
                for r in gr:
                    reasons[str(r)] += 1

        top_reasons = reasons.most_common(25)

        log_internal_review_access(
            request=request,
            confidence=None,
            result_count=int(sum(by_conf.values())),
            endpoint="metrics/seniority",
        )
        try:
            OrmAuditLogger().log(
                action="analysis.internal.metrics_seniority",
                actor_user_id=None,
                subject_user_id=None,
                ip=request.META.get("REMOTE_ADDR"),
                user_agent=request.headers.get("User-Agent"),
                metadata={"days": days, "analyses_count": int(sum(by_conf.values()))},
            )
        except Exception:
            logger.exception("audit log failed (ignored)")

        return Response(
            {
                "days": days,
                "analysesCount": int(sum(by_conf.values())),
                "bySeniorityConfidence": dict(by_conf),
                "topGatingReasons": [{"reason": r, "count": c} for r, c in top_reasons],
            }
        )


class SeniorityReviewSubmitView(APIView):
    """
    POST /analysis/internal/review/seniority

    Header: X-Analysis-Internal-Token
    Body: { "analysisKey", "reviewLabel": "intern|junior|mid|senior", "reviewNote?": "..." }
    """

    authentication_classes = []
    permission_classes = [HasAnalysisInternalReviewSecret]
    throttle_scope = "analysis_internal"

    def post(self, request):
        body = request.data if isinstance(request.data, dict) else {}
        analysis_key = str(body.get("analysisKey") or "").strip()
        raw_label = str(body.get("reviewLabel") or "").strip().lower()
        review_label = normalize_seniority_label(raw_label)
        note = str(body.get("reviewNote") or "").strip()[:2000]

        if not analysis_key or not review_label:
            return Response(
                {"detail": "Invalid or missing analysisKey / reviewLabel."},
                status=400,
            )

        salt = resolve_review_hash_salt()
        analysis = resolve_analysis_by_pseudo_key(analysis_key, salt=salt)
        if analysis is None:
            return Response({"detail": "Analysis not found."}, status=404)

        pj = dict(analysis.payload_json or {})
        ev = pj.get("seniorityEvidence")
        ev_list = list(ev) if isinstance(ev, list) else []
        ev_list.append(
            {
                "type": "human_review",
                "label": review_label,
                **({"note": note} if note else {}),
            }
        )
        pj["seniorityEvidence"] = ev_list[:24]
        pj["seniorityClass"] = review_label
        pj["seniorityConfidence"] = "high"
        pj["seniorityMlStatus"] = "human_review_override"

        ts = dict(analysis.task_scores or {})
        ts["seniority"] = SENIORITY_LABEL_TO_SCORE.get(review_label, 50)

        analysis.seniority_review_label = review_label
        analysis.seniority_final_label = review_label
        analysis.seniority_label_source = "review"
        analysis.seniority_confidence = "high"
        analysis.payload_json = pj
        analysis.task_scores = ts
        analysis.save(
            update_fields=[
                "seniority_review_label",
                "seniority_final_label",
                "seniority_label_source",
                "seniority_confidence",
                "payload_json",
                "task_scores",
                "updated_at",
            ]
        )

        log_internal_review_access(
            request=request,
            confidence=None,
            result_count=1,
            endpoint="review/seniority",
        )
        try:
            OrmAuditLogger().log(
                action="analysis.internal.review.seniority_set",
                actor_user_id=None,
                subject_user_id=None,
                ip=request.META.get("REMOTE_ADDR"),
                user_agent=request.headers.get("User-Agent"),
                metadata={
                    "analysis_key_suffix": analysis_key[-8:],
                    "review_label": review_label,
                    "has_note": bool(note),
                },
            )
        except Exception:
            logger.exception("audit log failed (ignored)")

        return Response(
            {
                "ok": True,
                "analysisKey": analysis_key,
                "seniorityFinalLabel": review_label,
                "seniorityLabelSource": "review",
            },
            status=200,
        )
