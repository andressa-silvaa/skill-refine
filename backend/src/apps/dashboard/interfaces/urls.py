from django.urls import include, path

app_name = "dashboard"

urlpatterns = [
    path("", include("apps.dashboard.interfaces.api.urls")),
]

