from django.urls import path

from .views import AiRewriteView

app_name = "analysis_api"

urlpatterns = [
    path("rewrite", AiRewriteView.as_view(), name="rewrite"),
]

