from __future__ import annotations

from django.urls import path

from .views import AvatarUploadView, PreferencesView, PrivacyDeleteAccountView, PrivacyExportView, ProfileView

urlpatterns = [
    path("", ProfileView.as_view(), name="profile"),
    path("avatar", AvatarUploadView.as_view(), name="avatar_upload"),
    path("preferences", PreferencesView.as_view(), name="preferences"),
    path("privacy/export", PrivacyExportView.as_view(), name="privacy_export"),
    path("privacy/delete", PrivacyDeleteAccountView.as_view(), name="privacy_delete"),
]

