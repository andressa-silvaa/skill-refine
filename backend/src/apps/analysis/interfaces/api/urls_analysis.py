"""
URLs for analysis run / latest / history. Mounted under /analysis/ in config.
"""
from django.urls import path

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
]
