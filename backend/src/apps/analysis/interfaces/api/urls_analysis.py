"""
URLs for analysis run / latest / history. Mounted under /analysis/ in config.
"""
from django.urls import path

from .internal_views import (
    LowConfidenceAnalysisExportView,
    LowConfidenceAnalysisReviewView,
    SeniorityInternalMetricsView,
    SeniorityReviewSubmitView,
)
from .views import (
    HistoryAnalysisView,
    LatestAnalysisView,
    RunAnalysisView,
)

app_name = "analysis_api"

urlpatterns = [
    path("run", RunAnalysisView.as_view(), name="run"),
    path("latest", LatestAnalysisView.as_view(), name="latest"),
    path("history", HistoryAnalysisView.as_view(), name="history"),
    path("internal/low-confidence", LowConfidenceAnalysisReviewView.as_view(), name="internal_low_confidence"),
    path(
        "internal/low-confidence/export",
        LowConfidenceAnalysisExportView.as_view(),
        name="internal_low_confidence_export",
    ),
    path(
        "internal/metrics/seniority",
        SeniorityInternalMetricsView.as_view(),
        name="internal_metrics_seniority",
    ),
    path(
        "internal/review/seniority",
        SeniorityReviewSubmitView.as_view(),
        name="internal_review_seniority",
    ),
]
