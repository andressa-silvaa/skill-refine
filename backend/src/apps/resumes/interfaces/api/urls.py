from django.urls import path

from .views import (
    ResumeDraftUpdateView,
    ResumeDuplicateView,
    ResumeListCreateView,
    ResumePdfDataView,
    ResumePdfTokenView,
    ResumePdfView,
)

app_name = "resumes_api"

urlpatterns = [
    path("resumes", ResumeListCreateView.as_view(), name="resumes_list_create"),
    path("resumes/<uuid:resume_id>", ResumeDraftUpdateView.as_view(), name="resumes_update"),
    path("resumes/<uuid:resume_id>/duplicate", ResumeDuplicateView.as_view(), name="resumes_duplicate"),
    path("resumes/<uuid:resume_id>/pdf-token", ResumePdfTokenView.as_view(), name="resumes_pdf_token"),
    path("resumes/<uuid:resume_id>/pdf-data", ResumePdfDataView.as_view(), name="resumes_pdf_data"),
    path("resumes/<uuid:resume_id>/pdf", ResumePdfView.as_view(), name="resumes_pdf"),
]
