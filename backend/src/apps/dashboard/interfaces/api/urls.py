from django.urls import path

from .views import DashboardSummaryView

app_name = "dashboard_api"

urlpatterns = [
    path("summary", DashboardSummaryView.as_view(), name="summary"),
]

