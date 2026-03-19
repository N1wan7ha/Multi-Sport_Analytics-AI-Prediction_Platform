"""Data pipeline URLs."""
from django.urls import path

from .views import PipelineStatusView

app_name = 'data_pipeline'

urlpatterns = [
    path('status/', PipelineStatusView.as_view(), name='pipeline-status'),
]
