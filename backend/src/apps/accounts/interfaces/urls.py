from django.urls import include, path

from apps.accounts.interfaces.profile.views import ProfileView


app_name = "accounts"

urlpatterns = [
    path("auth/", include("apps.accounts.interfaces.api.urls")),
    path("profile", ProfileView.as_view(), name="profile_no_slash"),
    path("profile/", include("apps.accounts.interfaces.profile.urls")),
]


