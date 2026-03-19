"""Predictions admin registration."""
from django.contrib import admin
from .models import PredictionJob, PredictionResult


@admin.register(PredictionJob)
class PredictionJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'match', 'prediction_type', 'status', 'model_version', 'requested_at']
    list_filter = ['status', 'prediction_type', 'model_version']
    search_fields = ['match__name']
    readonly_fields = ['requested_at', 'completed_at', 'celery_task_id']
    raw_id_fields = ['match', 'requested_by']


@admin.register(PredictionResult)
class PredictionResultAdmin(admin.ModelAdmin):
    list_display = ['job', 'team1', 'team2', 'team1_win_probability', 'team2_win_probability', 'confidence_score']
    raw_id_fields = ['job', 'team1', 'team2']
    readonly_fields = ['created_at']
