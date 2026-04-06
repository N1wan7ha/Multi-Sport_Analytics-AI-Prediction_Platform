"""Data pipeline URLs."""
from django.urls import path

from .views import PipelineStatusView, ManualMatchSyncView, GithubSyncView

app_name = 'data_pipeline'

urlpatterns = [
    path('status/', PipelineStatusView.as_view(), name='pipeline-status'),
    path('sync-match/', ManualMatchSyncView.as_view(), name='sync-match'),
    path('sync-github/', GithubSyncView.as_view(), name='sync-github'),
]
