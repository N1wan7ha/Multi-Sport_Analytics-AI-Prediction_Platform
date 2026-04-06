"""Django admin registration for data quality models."""
from django.contrib import admin
from .models import (
    RawSnapshot, CanonicalFieldSource, DataConflictLog,
    FeatureSnapshot, DataQualityReport
)


@admin.register(RawSnapshot)
class RawSnapshotAdmin(admin.ModelAdmin):
    list_display = ['provider', 'endpoint', 'status_code', 'is_valid', 'timestamp']
    list_filter = ['provider', 'endpoint', 'is_valid', 'timestamp']
    search_fields = ['endpoint']
    readonly_fields = ['payload', 'timestamp']
    ordering = ['-timestamp']


@admin.register(CanonicalFieldSource)
class CanonicalFieldSourceAdmin(admin.ModelAdmin):
    list_display = ['entity_type', 'entity_id', 'field_name', 'source_provider', 'confidence_score', 'source_timestamp']
    list_filter = ['entity_type', 'source_provider', 'confidence_score']
    search_fields = ['entity_id']
    readonly_fields = ['conflicting_values', 'updated_at']


@admin.register(DataConflictLog)
class DataConflictLogAdmin(admin.ModelAdmin):
    list_display = ['entity_type', 'entity_id', 'field_name', 'resolution_strategy', 'detected_at', 'resolved_at']
    list_filter = ['entity_type', 'resolution_strategy', 'detected_at']
    search_fields = ['entity_id', 'field_name']
    readonly_fields = ['conflicting_values', 'detected_at']


@admin.register(FeatureSnapshot)
class FeatureSnapshotAdmin(admin.ModelAdmin):
    list_display = ['match', 'window', 'captured_at', 'is_valid']
    list_filter = ['window', 'is_valid', 'captured_at']
    readonly_fields = ['features', 'created_at']


@admin.register(DataQualityReport)
class DataQualityReportAdmin(admin.ModelAdmin):
    list_display = ['report_date', 'teams_synced', 'players_synced', 'matches_synced', 'total_conflicts']
    list_filter = ['report_date']
    readonly_fields = ['provider_health', 'created_at']
