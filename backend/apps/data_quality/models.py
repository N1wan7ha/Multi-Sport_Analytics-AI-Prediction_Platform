"""Data quality models for Bronze/Silver/Gold layer architecture."""
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
import json


class RawSnapshot(models.Model):
    """Bronze layer: Unmodified API payloads before normalization."""
    
    PROVIDER_CHOICES = [
        ('rapidapi_free', 'RapidAPI Free Data'),
        ('cricbuzz2', 'Cricbuzz2'),
        ('livescore6', 'Livescore6'),
        ('cricapi', 'CricAPI'),
        ('apilayer_odds', 'APILayer Odds/Therundown'),
        ('web_scrape', 'Web Scrape'),
    ]
    
    ENDPOINT_CHOICES = [
        ('cricket_teams', '/cricket-teams'),
        ('cricket_players', '/cricket-players'),
        ('cricket_schedules', '/cricket-schedules'),
        ('cricket_livescores', '/cricket-livescores'),
        ('matches_v1_live', '/matches/v1/live'),
        ('matches_v2_list_live', '/matches/v2/list-live'),
        ('matches_v1_recent', '/matches/v1/recent'),
        ('matches_v1_upcoming', '/matches/v1/upcoming'),
        ('stats_v1_teams', '/stats/v1/teams'),
        ('stats_v1_players', '/stats/v1/players'),
        ('series_v1_', '/series/v1/'),
        ('apilayer_sports', '/sports'),
        ('apilayer_affiliates', '/affiliates'),
    ]
    
    # Source tracking
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        db_index=True
    )
    endpoint = models.CharField(
        max_length=50,
        choices=ENDPOINT_CHOICES,
        db_index=True
    )
    
    # Raw payload
    payload = models.JSONField()  # Unmodified API response
    status_code = models.IntegerField(default=200)
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    request_params = models.JSONField(default=dict, blank=True)  # Query params sent
    
    # Success tracking
    is_valid = models.BooleanField(default=True)  # Schema validation passed
    error_message = models.TextField(blank=True)  # Validation error details
    
    class Meta:
        db_table = 'raw_snapshots'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['provider', 'endpoint', '-timestamp']),
            models.Index(fields=['is_valid', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.provider} {self.endpoint} {self.timestamp}"


class CanonicalFieldSource(models.Model):
    """Silver layer: Field-level source tracking and confidence scoring."""
    
    ENTITY_TYPE_CHOICES = [
        ('team', 'Team'),
        ('player', 'Player'),
        ('match', 'Match'),
        ('venue', 'Venue'),
    ]
    
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES)
    entity_id = models.CharField(max_length=100)  # Team ID, Player ID, Match ID, etc.
    field_name = models.CharField(max_length=100)  # e.g., 'name', 'country', 'image_url'
    
    # Source tracking
    source_provider = models.CharField(max_length=20)  # Which API provided this?
    source_timestamp = models.DateTimeField()  # When was this data last synced?
    raw_snapshot = models.ForeignKey(
        RawSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='field_sources'
    )
    
    # Confidence (0-100)
    confidence_score = models.IntegerField(
        default=50,
        help_text="0-100: Lower for user-generated, higher for official API"
    )
    
    # Multiple sources observed?
    conflicting_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="Track {'value': confidence_score} for each conflicting observation"
    )
    
    # Canonical value
    canonical_value = models.TextField(null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'canonical_field_sources'
        unique_together = ('entity_type', 'entity_id', 'field_name')
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
        ]
    
    def __str__(self):
        return f"{self.entity_type}:{self.entity_id} {self.field_name}"


class DataConflictLog(models.Model):
    """Track conflicts detected when sources disagree on field values."""
    
    ENTITY_TYPE_CHOICES = [
        ('team', 'Team'),
        ('player', 'Player'),
        ('match', 'Match'),
        ('venue', 'Venue'),
    ]
    
    RESOLUTION_STRATEGY_CHOICES = [
        ('highest_confidence', 'Highest Confidence'),
        ('most_recent', 'Most Recent'),
        ('majority_vote', 'Majority Vote'),
        ('manual_review', 'Manual Review'),
    ]
    
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES)
    entity_id = models.CharField(max_length=100)
    field_name = models.CharField(max_length=100)
    
    # Conflicting values
    conflicting_values = models.JSONField()  # {'value': [provider1, provider2, ...], ...}
    
    # Resolution
    resolution_strategy = models.CharField(
        max_length=30,
        choices=RESOLUTION_STRATEGY_CHOICES,
        default='highest_confidence'
    )
    resolved_value = models.TextField(null=True, blank=True)
    
    # Audit trail
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.CharField(max_length=100, blank=True)  # User or system
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'data_conflict_logs'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['resolved_at']),
        ]
    
    def __str__(self):
        return f"{self.entity_type}:{self.entity_id} {self.field_name} conflict"


class FeatureSnapshot(models.Model):
    """Gold layer: ML-ready features captured at specific points in match lifecycle."""
    
    WINDOW_CHOICES = [
        ('pre_match', 'Pre-Match'),      # Before match start
        ('powerplay', 'Powerplay'),      # First 6 overs
        ('middle_overs', 'Middle Overs'), # 7-15 overs
        ('death_overs', 'Death Overs'),  # 16-20 overs
        ('full_match', 'Full Match'),    # Post-match
    ]
    
    match = models.ForeignKey(
        'matches.Match',
        on_delete=models.CASCADE,
        related_name='feature_snapshots'
    )
    
    # Window timing
    window = models.CharField(max_length=20, choices=WINDOW_CHOICES)
    captured_at = models.DateTimeField()  # When was this snapshot taken?
    
    # Frozen features (pre-computed, will not change)
    features = models.JSONField()  # All computed features for this window
    
    # Source tracking
    sources_used = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True
    )  # Which providers contributed to these features?
    
    # ML ready
    is_valid = models.BooleanField(default=True)  # Passed validation checks
    validation_errors = models.JSONField(default=list, blank=True)  # NaN, missing, etc.
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'feature_snapshots'
        unique_together = ('match', 'window')
        indexes = [
            models.Index(fields=['match', 'window']),
            models.Index(fields=['is_valid']),
        ]
    
    def __str__(self):
        return f"{self.match} {self.window}"


class DataQualityReport(models.Model):
    """Summary metrics on data quality per sync window."""
    
    # Reporting window
    report_date = models.DateField(auto_now_add=True, db_index=True)
    
    # Sync results
    teams_synced = models.IntegerField(default=0)
    teams_conflicts = models.IntegerField(default=0)
    players_synced = models.IntegerField(default=0)
    players_conflicts = models.IntegerField(default=0)
    matches_synced = models.IntegerField(default=0)
    matches_incomplete = models.IntegerField(default=0)  # Missing stats
    
    # Source health
    provider_health = models.JSONField(default=dict)  # {'provider': {'success_rate': 0.95, 'response_time_ms': 450, ...}}
    
    # Conflicts detected
    total_conflicts = models.IntegerField(default=0)
    auto_resolved = models.IntegerField(default=0)
    manual_review_needed = models.IntegerField(default=0)
    
    # Data completeness
    matches_with_complete_stats = models.IntegerField(default=0)  # % matching scorecard coverage
    field_coverage_percent = models.FloatField(default=0.0)  # Avg non-null fields across entities
    
    # ML readiness
    features_captured = models.IntegerField(default=0)  # FeatureSnapshot rows
    features_valid = models.IntegerField(default=0)  # Non-null, in-range
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'data_quality_reports'
        ordering = ['-report_date']
    
    def __str__(self):
        return f"Quality Report {self.report_date}"
