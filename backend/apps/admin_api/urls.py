"""Admin API URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'admin_api'

router = DefaultRouter()
router.register(r'users', views.AdminUserViewSet, basename='admin-users')

urlpatterns = [
    path('', include(router.urls)),
    path('activity-summary/', views.ActivitySummaryView.as_view(), name='activity-summary'),
    path('pipeline/status/', views.AdminPipelineStatusView.as_view(), name='pipeline-status'),
    path('pipeline/trigger/', views.AdminPipelineTriggerView.as_view(), name='pipeline-trigger'),
    path('pipeline/trigger-bulk/', views.AdminPipelineBulkTriggerView.as_view(), name='pipeline-trigger-bulk'),
    path('models/ranking/', views.AdminModelRankingView.as_view(), name='models-ranking'),
    path('system-metrics/', views.SystemMetricsView.as_view(), name='system-metrics'),
    path('prediction-jobs/', views.AdminPredictionJobsView.as_view(), name='prediction-jobs'),
    path('prediction-jobs/bulk-action/', views.AdminPredictionBulkActionView.as_view(), name='prediction-jobs-bulk-action'),
    path('prediction-jobs/<int:job_id>/', views.AdminPredictionJobDetailView.as_view(), name='prediction-jobs-detail'),
    path('prediction-jobs/<int:job_id>/cancel/', views.AdminPredictionCancelView.as_view(), name='prediction-jobs-cancel'),
    path('prediction-jobs/<int:job_id>/retry/', views.AdminPredictionRetryView.as_view(), name='prediction-jobs-retry'),
]
