"""Analysis worker: run inference and persist result. Used by Celery task and thread fallback."""
from __future__ import annotations

import logging
import time

from django.utils import timezone

from apps.analysis.application.inference.orchestrator import analyze_resume
from apps.analysis.application.inference.safety import safe_error_message
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.dashboard.interfaces.api.cache import invalidate_dashboard_summary_cache
from apps.resumes.interfaces.api.payloads import resume_detail_payload

logger = logging.getLogger(__name__)


def _get_user_language(user_id: str) -> str:
    try:
        from apps.accounts.infrastructure.models import UserPreferences

        prefs = UserPreferences.objects.filter(user_id=user_id).first()
        if prefs and getattr(prefs, "language", None):
            return str(prefs.language)
    except Exception:
        pass
    return "pt-BR"


def run_analysis_worker(analysis_id: str) -> None:
    """
    Load analysis + resume, run inference, persist result.
    Raises on failure; caller handles DB updates and cache invalidation.
    """
    analysis = (
        ResumeAnalysis.objects.select_related("resume", "user")
        .prefetch_related(
            "resume__resumecontact",
            "resume__resumeexperience_set__resumeexperiencebullet_set",
            "resume__resumeeducation_set",
            "resume__resumeskill_set",
            "resume__resumelanguage_set",
        )
        .get(id=analysis_id)
    )

    analysis.status = AnalysisStatus.RUNNING
    analysis.save(update_fields=["status", "updated_at"])
    queue_wait_ms = int((timezone.now() - analysis.created_at).total_seconds() * 1000)
    start = time.monotonic()

    resume = analysis.resume
    resume_data = resume_detail_payload(resume)
    language = _get_user_language(str(analysis.user_id))
    job_text = (analysis.job_description_text or "").strip() or None

    result = analyze_resume(
        resume_data=resume_data,
        job_description_text=job_text,
        language=language,
    )

    analysis.score = result["score"]
    analysis.task_scores = result["task_scores"]
    analysis.payload_json = result["payload_json"]
    analysis.model_name = result.get("model_name", "")
    analysis.model_version = result.get("model_version", "")
    analysis.dataset_version = result.get("dataset_version", "")
    analysis.provider = result.get("provider", "local")
    analysis.seniority_rule_label = result.get("seniority_rule_label", "") or ""
    analysis.seniority_final_label = result.get("seniority_final_label", "") or ""
    analysis.seniority_label_source = result.get("seniority_label_source", "") or "rule_policy"
    analysis.seniority_policy_version = result.get("seniority_policy_version", "") or ""
    analysis.seniority_confidence = result.get("seniority_confidence_persist", "") or ""
    analysis.seniority_evidence = result.get("seniority_evidence_json")
    analysis.seniority_text_label = result.get("seniority_text_label", "") or ""
    analysis.seniority_text_confidence = result.get("seniority_text_confidence", "") or ""
    analysis.target_fit_embedding_score = result.get("target_fit_embedding_score")
    analysis.target_fit_signals_score = result.get("target_fit_signals_score")
    analysis.target_fit_final_score = result.get("target_fit_final_score")
    analysis.status = AnalysisStatus.DONE
    analysis.save(
        update_fields=[
            "status",
            "score",
            "task_scores",
            "payload_json",
            "model_name",
            "model_version",
            "dataset_version",
            "provider",
            "seniority_rule_label",
            "seniority_final_label",
            "seniority_label_source",
            "seniority_policy_version",
            "seniority_confidence",
            "seniority_evidence",
            "seniority_text_label",
            "seniority_text_confidence",
            "target_fit_embedding_score",
            "target_fit_signals_score",
            "target_fit_final_score",
            "updated_at",
        ]
    )

    duration_ms = int((time.monotonic() - start) * 1000)
    pj = analysis.payload_json or {}
    ts = analysis.task_scores or {}
    logger.info(
        "Analysis task completed",
        extra={
            "analysis_id": str(analysis.id),
            "resume_id": str(analysis.resume_id),
            "model_version": analysis.model_version,
            "provider": analysis.provider,
            "duration_ms": duration_ms,
            "queue_wait_ms": queue_wait_ms,
            "completeness_score": (pj.get("completeness") or {}).get("score"),
            "completeness_level": (pj.get("completeness") or {}).get("level"),
            "seniority_confidence": pj.get("seniorityConfidence"),
            "seniority_rule_base": pj.get("seniorityRuleBase"),
            "seniority_final": pj.get("seniorityClass"),
            "seniority_ml_status": pj.get("seniorityMlStatus"),
            "quality_score": analysis.score,
        },
    )
    logger.info(
        "analysis_score_components",
        extra={
            "analysis_id": str(analysis.id),
            "resume_id": str(analysis.resume_id),
            "score_overall": analysis.score,
            "quality_task": ts.get("ats"),
            "seniority_task": ts.get("seniority"),
            "matching_task": ts.get("matching"),
            "target_fit_task": ts.get("target_fit"),
            "target_seniority_task": ts.get("target_seniority"),
            "seniority_label_source": analysis.seniority_label_source,
        },
    )
    invalidate_dashboard_summary_cache(str(analysis.user_id))
    try:
        from apps.notifications.services import create_notification

        create_notification(
            user_id=str(analysis.user_id),
            type="analysis_done",
            title_key="notifications.analysisDone",
            params={"name": (resume.name or resume.target_position or "Currículo")[:80]},
            action_url=f"/protected/ai-analysis?resumeId={resume.id}",
            entity_ref={"analysis_id": str(analysis.id), "resume_id": str(resume.id)},
        )
    except Exception as exc:
        logger.warning("Failed to create analysis_done notification: %s", exc)


def run_analysis_worker_safe(analysis_id: str) -> None:
    """
    Run worker with exception handling. Updates status to FAILED on error.
    Used by Celery task and thread fallback.
    """
    try:
        run_analysis_worker(analysis_id)
    except ResumeAnalysis.DoesNotExist:
        logger.warning("Analysis task: record not found", extra={"analysis_id": analysis_id})
    except Exception as exc:
        logger.exception(
            "Analysis task failed",
            extra={"analysis_id": analysis_id, "error": safe_error_message(exc)},
        )
        try:
            ResumeAnalysis.objects.filter(id=analysis_id).update(
                status=AnalysisStatus.FAILED,
                error_message=safe_error_message(exc, max_len=2000),
            )
        except Exception:
            pass
        try:
            a = ResumeAnalysis.objects.filter(id=analysis_id).select_related("resume").first()
            if a:
                invalidate_dashboard_summary_cache(str(a.user_id))
                from apps.notifications.services import create_notification

                resume_name = (a.resume.name or a.resume.target_position or "Currículo")[:80] if a.resume else "Currículo"
                create_notification(
                    user_id=str(a.user_id),
                    type="analysis_failed",
                    title_key="notifications.analysisFailed",
                    params={"name": resume_name},
                    action_url=f"/protected/ai-analysis",
                    entity_ref={"analysis_id": str(a.id), "resume_id": str(a.resume_id) if a.resume_id else ""},
                )
        except Exception:
            pass
        raise
