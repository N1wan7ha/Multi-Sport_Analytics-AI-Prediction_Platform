"""Serializers for admin API endpoints."""
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    """Minimal user serializer for admin user management."""
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'role', 'is_active', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']


class ActivitySummarySerializer(serializers.Serializer):
    """Activity summary across the platform."""
    new_registrations_7d = serializers.IntegerField()
    new_registrations_30d = serializers.IntegerField()
    prediction_requests_total = serializers.IntegerField()
    pre_match = serializers.IntegerField()
    live = serializers.IntegerField()
    active_users_7d = serializers.IntegerField()
    syncs_24h = serializers.IntegerField()


class PipelineStatusSnapshotSerializer(serializers.Serializer):
    current_matches = serializers.IntegerField()
    live_matches = serializers.IntegerField()
    completed_matches = serializers.IntegerField()
    player_stats = serializers.IntegerField()
    unified_matches = serializers.IntegerField()
    last_model_retraining = serializers.CharField(allow_blank=True)
    endpoint_health = serializers.JSONField(required=False)
    endpoint_health_history = serializers.JSONField(required=False)
    livescore6_endpoint_health = serializers.JSONField(required=False)


class PipelineTaskTriggerSerializer(serializers.Serializer):
    task_name = serializers.ChoiceField(
        choices=[
            'sync_current_matches',
            'sync_cricbuzz_live',
            'sync_completed_matches',
            'sync_player_stats',
            'sync_unified_matches',
            'sync_rapidapi_teams',
            'sync_rapidapi_players',
            'sync_rapidapi_team_logos',
            'run_model_retraining_pipeline',
            'run_rolling_window_retraining_pipeline',
        ]
    )
    team_id = serializers.IntegerField(required=False, min_value=1)


class PipelineBulkTriggerSerializer(serializers.Serializer):
    bundle_name = serializers.ChoiceField(
        choices=[
            'rapidapi_catalog',
            'match_sync',
            'full_refresh',
        ]
    )
    team_id = serializers.IntegerField(required=False, min_value=1)


class SystemMetricsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    live_matches = serializers.IntegerField()
    queued_predictions = serializers.IntegerField()
    processing_predictions = serializers.IntegerField()
    failed_predictions = serializers.IntegerField()
    completed_predictions = serializers.IntegerField()


class AdminPredictionJobSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    match_id = serializers.IntegerField()
    match_name = serializers.CharField()
    requested_by_id = serializers.IntegerField(allow_null=True)
    requested_by_email = serializers.CharField(allow_blank=True)
    prediction_type = serializers.CharField()
    status = serializers.CharField()
    model_version = serializers.CharField()
    celery_task_id = serializers.CharField(allow_blank=True)
    error_message = serializers.CharField(allow_blank=True)
    requested_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)


class AdminPredictionRetrySerializer(serializers.Serializer):
    current_over = serializers.IntegerField(required=False, min_value=0)
    current_score = serializers.CharField(required=False, allow_blank=True, max_length=50)


class AdminPredictionBulkActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['cancel', 'retry'])
    job_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=200,
    )
    current_over = serializers.IntegerField(required=False, min_value=0)
    current_score = serializers.CharField(required=False, allow_blank=True, max_length=50)
