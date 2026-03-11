"""Notifications API URLs."""
from django.urls import path

from .views import (
    NotificationClearAllView,
    NotificationDeleteView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
)

app_name = "notifications_api"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("unread-count/", NotificationUnreadCountView.as_view(), name="unread_count"),
    path("read-all/", NotificationMarkAllReadView.as_view(), name="read_all"),
    path("clear-all/", NotificationClearAllView.as_view(), name="clear_all"),
    path("<uuid:notification_id>/read/", NotificationMarkReadView.as_view(), name="mark_read"),
    path("<uuid:notification_id>/", NotificationDeleteView.as_view(), name="delete"),
]
