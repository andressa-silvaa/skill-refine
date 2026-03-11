"""Search API URLs."""
from django.urls import path

from .views import GlobalSearchView

app_name = "search_api"

urlpatterns = [
    path("", GlobalSearchView.as_view(), name="search"),
]
