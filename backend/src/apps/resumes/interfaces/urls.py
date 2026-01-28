from django.urls import include, path


app_name = "resumes"

urlpatterns = [
    path("api/", include("apps.resumes.interfaces.api.urls")),
]


