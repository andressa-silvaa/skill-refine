from django.urls import include, path

from config.views import HealthcheckView


urlpatterns = [
    path("health", HealthcheckView.as_view(), name="health"),
    path("ai/", include("apps.analysis.interfaces.api.urls")),
    path("accounts/", include("apps.accounts.interfaces.urls")),
    path("resumes/", include("apps.resumes.interfaces.urls")),
    path("analysis/", include("apps.analysis.interfaces.urls")),
    path("dashboard/", include("apps.dashboard.interfaces.api.urls")),
    path("notifications/", include("apps.notifications.interfaces.api.urls")),
    path("search/", include("apps.search.urls")),
]


