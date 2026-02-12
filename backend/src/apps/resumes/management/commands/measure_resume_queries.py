"""
Measure query count and response time for resume list and detail endpoints.
Run: python manage.py measure_resume_queries [--json]
Uses CaptureQueriesContext so it works regardless of DEBUG.
"""
from __future__ import annotations

import json
import time

from django.core.management.base import BaseCommand
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from apps.accounts.infrastructure.models import User
from apps.resumes.infrastructure.models import (
    Resume,
    ResumeContact,
    ResumeEducation,
    ResumeExperience,
    ResumeExperienceBullet,
    ResumeLanguage,
    ResumeSkill,
    ResumeStatus,
    ResumeTag,
)
from apps.resumes.interfaces.api.views import (
    ResumeDraftUpdateView,
    ResumeListCreateView,
)


def ensure_fixtures():
    """Get or create a user with a few resumes (with tags, skills, experiences)."""
    user, _ = User.objects.get_or_create(
        email="measure-queries@test.local",
        defaults={
            "full_name": "Measure Queries User",
            "status": "active",
        },
    )
    resumes = list(
        Resume.objects.filter(user_id=user.id, deleted_at__isnull=True).order_by("-updated_at")[:3]
    )
    if len(resumes) < 2:
        for i in range(2 - len(resumes)):
            r = Resume.objects.create(
                user_id=user.id,
                name=f"Resume measure {i}",
                status=ResumeStatus.DRAFT,
                target_position="Developer",
            )
            ResumeTag.objects.get_or_create(
                resume=r, defaults={"label": f"Tag-{r.id}", "position_index": 0}
            )
            ResumeSkill.objects.get_or_create(
                resume=r, defaults={"name": "Python", "position_index": 0}
            )
            ResumeContact.objects.get_or_create(
                resume=r, defaults={"full_name": "Test", "email": "a@b.com"}
            )
            exp = ResumeExperience.objects.create(
                resume=r, company="Co", position="Dev", position_index=0
            )
            ResumeExperienceBullet.objects.create(
                experience=exp, content="Bullet", position_index=0
            )
            ResumeEducation.objects.create(
                resume=r, institution="Uni", course="CS", position_index=0
            )
            ResumeLanguage.objects.create(
                resume=r, name="English", level="intermediate", position_index=0
            )
            resumes.insert(0, r)
    all_resumes = list(
        Resume.objects.filter(user_id=user.id, deleted_at__isnull=True).order_by("-updated_at")
    )
    detail_resume = all_resumes[0] if all_resumes else None
    return user, all_resumes, detail_resume


def run_measurements():
    """Run list and detail once each; return dict with query counts and times (ms)."""
    user, items, detail_resume = ensure_fixtures()
    factory = RequestFactory()

    # List
    request = factory.get("/resumes/api/resumes/")
    request.user = user
    list_view = ResumeListCreateView.as_view()
    with CaptureQueriesContext(connection) as ctx:
        t0 = time.perf_counter()
        response = list_view(request)
        list_time_ms = (time.perf_counter() - t0) * 1000
    list_queries = len(ctx.captured_queries)

    # Detail
    detail_queries = 0
    detail_time_ms = 0.0
    if detail_resume:
        request = factory.get(f"/resumes/api/resumes/{detail_resume.id}/")
        request.user = user
        detail_view = ResumeDraftUpdateView.as_view()
        with CaptureQueriesContext(connection) as ctx:
            t0 = time.perf_counter()
            response = detail_view(request, resume_id=detail_resume.id)
            detail_time_ms = (time.perf_counter() - t0) * 1000
        detail_queries = len(ctx.captured_queries)

    return {
        "n_resumes": len(items),
        "list_queries": list_queries,
        "list_time_ms": round(list_time_ms, 2),
        "detail_queries": detail_queries,
        "detail_time_ms": round(detail_time_ms, 2),
    }


class Command(BaseCommand):
    help = "Measure query count and time for resume list and detail endpoints (current code = AFTER N+1 fix)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output only JSON for scripting.",
        )

    def handle(self, *args, **options):
        data = run_measurements()
        if options.get("json"):
            self.stdout.write(json.dumps(data))
            return
        self.stdout.write(f"N_RESUMES: {data['n_resumes']}")
        self.stdout.write(f"LIST_QUERIES: {data['list_queries']}")
        self.stdout.write(f"LIST_TIME_MS: {data['list_time_ms']}")
        self.stdout.write(f"DETAIL_QUERIES: {data['detail_queries']}")
        self.stdout.write(f"DETAIL_TIME_MS: {data['detail_time_ms']}")
