from django.urls import path

from .pdf_views import ResumePdfStartView, ResumePdfStatusView, ResumePdfView
from .resume_views import (
    ResumeDraftUpdateView,
    ResumeDuplicateView,
    ResumeListCreateView,
    ResumePdfDataView,
    ResumePdfTokenView,
)
from .version_views import ResumeVersionDetailView, ResumeVersionListView, ResumeVersionRestoreView

app_name = "resumes_api"

urlpatterns = [
    path("resumes", ResumeListCreateView.as_view(), name="resumes_list_create"),
    path("resumes/<uuid:resume_id>", ResumeDraftUpdateView.as_view(), name="resumes_update"),
    path("resumes/<uuid:resume_id>/duplicate", ResumeDuplicateView.as_view(), name="resumes_duplicate"),
    path("resumes/<uuid:resume_id>/pdf-token", ResumePdfTokenView.as_view(), name="resumes_pdf_token"),
    path("resumes/<uuid:resume_id>/pdf-data", ResumePdfDataView.as_view(), name="resumes_pdf_data"),
    path("resumes/<uuid:resume_id>/pdf/start", ResumePdfStartView.as_view(), name="resumes_pdf_start"),
    path(
        "resumes/<uuid:resume_id>/pdf/status/<uuid:export_id>",
        ResumePdfStatusView.as_view(),
        name="resumes_pdf_status",
    ),
    path("resumes/<uuid:resume_id>/pdf", ResumePdfView.as_view(), name="resumes_pdf"),
    path("versions", ResumeVersionListView.as_view(), name="versions_list"),
    path(
        "resumes/<uuid:resume_id>/versions/<uuid:version_id>",
        ResumeVersionDetailView.as_view(),
        name="versions_detail",
    ),
    path(
        "resumes/<uuid:resume_id>/versions/<uuid:version_id>/restore",
        ResumeVersionRestoreView.as_view(),
        name="versions_restore",
    ),
]
