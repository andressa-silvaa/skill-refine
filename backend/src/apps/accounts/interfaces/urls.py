from django.urls import include, path


app_name = "accounts"

urlpatterns = [
    path("auth/", include("apps.accounts.interfaces.api.urls")),
]


