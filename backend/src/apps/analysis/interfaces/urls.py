from django.urls import include, path

app_name = "analysis"

urlpatterns = [
    path("", include("apps.analysis.interfaces.api.urls_analysis")),
]


