"""Serializers for data quality models."""
from rest_framework import serializers
from .models import (
    DataQualityReport, DataConflictLog, RawSnapshot, CanonicalFieldSource,
    FeatureSnapshot
)


class RawSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawSnapshot
        fields = ['id', 'provider', 'endpoint', 'status_code', 'is_valid', 'timestamp', 'response_time_ms']


class CanonicalFieldSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CanonicalFieldSource
        fields = [
            'entity_type', 'entity_id', 'field_name', 'source_provider',
            'confidence_score', 'canonical_value', 'conflicting_values'
        ]


class DataConflictLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataConflictLog
        fields = [
            'id', 'entity_type', 'entity_id', 'field_name',
            'conflicting_values', 'resolution_strategy', 'resolved_value',
            'detected_at', 'resolved_at', 'resolved_by', 'notes'
        ]


class FeatureSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureSnapshot
        fields = [
            'id', 'match', 'window', 'captured_at', 'is_valid',
            'features', 'sources_used', 'validation_errors'
        ]


class DataQualityReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataQualityReport
        fields = [
            'id', 'report_date', 'teams_synced', 'teams_conflicts',
            'players_synced', 'players_conflicts', 'matches_synced',
            'matches_incomplete', 'provider_health', 'total_conflicts',
            'auto_resolved', 'manual_review_needed', 'matches_with_complete_stats',
            'field_coverage_percent', 'features_captured', 'features_valid', 'notes'
        ]
        read_only_fields = ['report_date', 'created_at']
