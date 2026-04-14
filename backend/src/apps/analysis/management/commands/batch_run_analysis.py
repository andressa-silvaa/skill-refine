"""
Run analysis for many resumes (same code path as POST /analysis/run).

  python manage.py batch_run_analysis --user-email dev@local.test --limit 50 --concurrency 4 --sync --only-missing

Use --sync for local/tests without Celery. In production, omit --sync and ensure Celery workers are running.
Logs use pseudo resume_key / analysis_key only (no CV text).
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.infrastructure.models import User
from apps.analysis.application.internal_review import pseudo_key, resolve_review_hash_salt
from apps.analysis.interfaces.api.services import get_latest_analysis, run_analysis
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume

logger = logging.getLogger(__name__)


def _parse_since(raw: str | None) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _resume_has_valid_done(user_id: str, resume: Resume) -> bool:
    latest = get_latest_analysis(user_id, str(resume.id))
    return latest is not None and latest.status == AnalysisStatus.DONE


class Command(BaseCommand):
    help = "Batch-enqueue or sync-run ResumeAnalysis for a user's resumes."

    def add_arguments(self, parser):
        parser.add_argument("--user-email", type=str, default="", dest="user_email")
        parser.add_argument("--user-id", type=str, default="", dest="user_id")
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--concurrency", type=int, default=5)
        parser.add_argument("--sleep-ms", type=int, default=50, dest="sleep_ms")
        parser.add_argument("--retry", type=int, default=0, help="Retries per resume on FAILED (new analysis row each time).")
        parser.add_argument("--only-missing", action="store_true", dest="only_missing")
        parser.add_argument("--since", type=str, default="", help="ISO datetime: only resumes updated at/after this.")
        parser.add_argument(
            "--resume-tag",
            type=str,
            default="seed_synthetic",
            dest="resume_tag",
            help="Only resumes with this ResumeTag label (empty = all user's resumes; use with care).",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run worker inline (no Celery/thread queue). Recommended for tests and dev without broker.",
        )
        parser.add_argument("--job-timeout-s", type=int, default=240, dest="job_timeout_s")
        parser.add_argument("--name-prefix", type=str, default="", dest="name_prefix", help="Filter resume.name startswith.")

    def handle(self, *args, **options):
        email = (options.get("user_email") or "").strip()
        uid = (options.get("user_id") or "").strip()
        limit = max(1, min(int(options["limit"]), 20_000))
        concurrency = max(1, min(int(options["concurrency"]), 64))
        sleep_ms = max(0, int(options["sleep_ms"]))
        retries = max(0, min(int(options["retry"]), 5))
        only_missing = bool(options.get("only_missing"))
        tag = (options.get("resume_tag") or "").strip()
        name_prefix = (options.get("name_prefix") or "").strip()
        sync = bool(options.get("sync"))
        job_timeout_s = max(30, int(options["job_timeout_s"]))
        since_dt = _parse_since((options.get("since") or "").strip())

        if not email and not uid:
            raise CommandError("Provide --user-email or --user-id.")

        if uid:
            user = User.objects.filter(id=uid, deleted_at__isnull=True).first()
        else:
            user = User.objects.filter(email__iexact=email, deleted_at__isnull=True).first()
        if user is None:
            raise CommandError("User not found.")

        qs = Resume.objects.filter(user_id=user.id, deleted_at__isnull=True).order_by("created_at")
        if tag:
            qs = qs.filter(resumetag__label=tag).distinct()
        if name_prefix:
            qs = qs.filter(name__istartswith=name_prefix)
        if since_dt is not None:
            qs = qs.filter(updated_at__gte=since_dt)

        resume_ids = list(qs.values_list("id", flat=True)[:limit])
        if not resume_ids:
            self.stdout.write(self.style.WARNING("No resumes matched filters."))
            return

        salt = resolve_review_hash_salt()
        done = failed = skipped = 0

        def run_one(rid) -> str:
            resume = Resume.objects.filter(pk=rid).first()
            if resume is None:
                return "missing"
            rk = pseudo_key(raw_id=str(rid), salt=salt)
            if only_missing and _resume_has_valid_done(str(user.id), resume):
                logger.info("batch_analysis_skipped", extra={"resume_key": rk, "reason": "valid_done_exists"})
                return "skipped"
            attempts = 0
            while attempts <= retries:
                analysis, err = run_analysis(str(user.id), str(rid), None, sync=sync)
                if analysis is None:
                    logger.warning("batch_analysis_enqueue_failed", extra={"resume_key": rk, "error": err})
                    return "failed"
                aid = str(analysis.id)
                ak = pseudo_key(raw_id=aid, salt=salt)
                if sync:
                    a = ResumeAnalysis.objects.filter(pk=analysis.id).first()
                    st = a.status if a else "missing"
                    logger.info("batch_analysis_sync_done", extra={"resume_key": rk, "analysis_key": ak, "status": st})
                    return "done" if st == AnalysisStatus.DONE else "failed"

                deadline = time.monotonic() + job_timeout_s
                while time.monotonic() < deadline:
                    a = ResumeAnalysis.objects.filter(pk=analysis.id).only("status").first()
                    if a is None:
                        return "failed"
                    if a.status == AnalysisStatus.DONE:
                        logger.info("batch_analysis_done", extra={"resume_key": rk, "analysis_key": ak})
                        return "done"
                    if a.status == AnalysisStatus.FAILED:
                        break
                    time.sleep(0.4)
                a = ResumeAnalysis.objects.filter(pk=analysis.id).only("status").first()
                if a and a.status == AnalysisStatus.DONE:
                    return "done"
                attempts += 1
                if attempts <= retries:
                    logger.info("batch_analysis_retry", extra={"resume_key": rk, "attempt": attempts})
                    continue
                logger.warning("batch_analysis_failed", extra={"resume_key": rk, "analysis_key": ak})
                return "failed"
            return "failed"

        if sync:
            for i, rid in enumerate(resume_ids):
                r = run_one(rid)
                if r == "done":
                    done += 1
                elif r == "skipped":
                    skipped += 1
                else:
                    failed += 1
                if sleep_ms and i + 1 < len(resume_ids):
                    time.sleep(sleep_ms / 1000.0)
        else:
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                futures = []
                for i, rid in enumerate(resume_ids):
                    futures.append(pool.submit(run_one, rid))
                    if sleep_ms:
                        time.sleep(sleep_ms / 1000.0)
                for fut in as_completed(futures):
                    r = fut.result()
                    if r == "done":
                        done += 1
                    elif r == "skipped":
                        skipped += 1
                    else:
                        failed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Batch finished: done={done} failed={failed} skipped={skipped} "
                f"(resumes_selected={len(resume_ids)} sync={sync}) at {timezone.now().isoformat()}"
            )
        )
