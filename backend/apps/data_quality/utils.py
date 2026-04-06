"""Data pipeline utilities for Bronze/Silver/Gold layer architecture."""
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

import httpx
from django.utils import timezone

from apps.data_quality.models import (
    RawSnapshot, CanonicalFieldSource, DataConflictLog, DataQualityReport
)
from apps.data_quality.conflict_resolver import FieldSourceManager

logger = logging.getLogger(__name__)


def write_raw_snapshot(
    provider: str,
    endpoint: str,
    payload: Dict[str, Any],
    status_code: int = 200,
    response_time_ms: Optional[int] = None,
    request_params: Optional[Dict] = None,
    is_valid: bool = True,
    error_message: str = '',
) -> RawSnapshot:
    """Write unmodified API payload to Bronze layer."""
    return RawSnapshot.objects.create(
        provider=provider,
        endpoint=endpoint,
        payload=payload,
        status_code=status_code,
        response_time_ms=response_time_ms,
        request_params=request_params or {},
        is_valid=is_valid,
        error_message=error_message,
        timestamp=timezone.now(),
    )


def update_team_source(
    team_obj,
    field_name: str,
    value: Any,
    provider: str,
    confidence_score: int = 60,
    raw_snapshot_id: Optional[int] = None,
) -> None:
    """Update team field source with conflict detection."""
    conflict_detected, _ = FieldSourceManager.update_field_source(
        entity_type='team',
        entity_id=str(team_obj.id),
        field_name=field_name,
        value=value,
        provider=provider,
        confidence_score=confidence_score,
        timestamp=timezone.now(),
        raw_snapshot_id=raw_snapshot_id,
    )
    
    # Update canonical field
    setattr(team_obj, field_name, value)
    team_obj.primary_source = provider
    team_obj.confidence_score = max(team_obj.confidence_score, confidence_score)
    
    # Track source
    if not team_obj.source_urls:
        team_obj.source_urls = []
    team_obj.source_urls.append({
        'provider': provider,
        'timestamp': timezone.now().isoformat(),
        'field': field_name,
    })


def update_player_source(
    player_obj,
    field_name: str,
    value: Any,
    provider: str,
    confidence_score: int = 60,
    raw_snapshot_id: Optional[int] = None,
) -> None:
    """Update player field source with conflict detection."""
    conflict_detected, _ = FieldSourceManager.update_field_source(
        entity_type='player',
        entity_id=str(player_obj.id),
        field_name=field_name,
        value=value,
        provider=provider,
        confidence_score=confidence_score,
        timestamp=timezone.now(),
        raw_snapshot_id=raw_snapshot_id,
    )
    
    # Update canonical field
    setattr(player_obj, field_name, value)
    player_obj.primary_source = provider
    player_obj.confidence_score = max(player_obj.confidence_score, confidence_score)
    
    # Track source
    if not player_obj.source_urls:
        player_obj.source_urls = []
    player_obj.source_urls.append({
        'provider': provider,
        'timestamp': timezone.now().isoformat(),
        'field': field_name,
    })


def update_match_source(
    match_obj,
    field_name: str,
    value: Any,
    provider: str,
    confidence_score: int = 60,
    raw_snapshot_id: Optional[int] = None,
) -> None:
    """Update match field source with conflict detection."""
    conflict_detected, _ = FieldSourceManager.update_field_source(
        entity_type='match',
        entity_id=str(match_obj.id),
        field_name=field_name,
        value=value,
        provider=provider,
        confidence_score=confidence_score,
        timestamp=timezone.now(),
        raw_snapshot_id=raw_snapshot_id,
    )
    
    # Update canonical field
    setattr(match_obj, field_name, value)
    match_obj.primary_source = provider
    match_obj.confidence_score = max(match_obj.confidence_score, confidence_score)
    
    # Track source
    if not match_obj.source_urls:
        match_obj.source_urls = []
    match_obj.source_urls.append({
        'provider': provider,
        'timestamp': timezone.now().isoformat(),
        'field': field_name,
    })


def generate_data_quality_report(report_date=None) -> DataQualityReport:
    """Generate daily data quality metrics."""
    from apps.matches.models import Team, Match
    from apps.players.models import Player
    
    if report_date is None:
        report_date = timezone.now().date()
    
    # Count synced entities
    teams_synced = Team.objects.count()
    players_synced = Player.objects.count()
    matches_synced = Match.objects.count()
    
    # Count conflicts
    total_conflicts = DataConflictLog.objects.filter(
        detected_at__date=report_date
    ).count()
    auto_resolved = DataConflictLog.objects.filter(
        detected_at__date=report_date,
        resolved_at__isnull=False,
    ).count()
    manual_review_needed = total_conflicts - auto_resolved
    
    # Check completeness
    matches_with_complete_stats = Match.objects.filter(
        stats_completeness__gte=0.8
    ).count()
    
    # Provider health from RawSnapshot
    provider_health = {}
    for provider in ['rapidapi_free', 'cricbuzz2', 'cricapi', 'apilayer_odds', 'web_scrape']:
        total = RawSnapshot.objects.filter(
            provider=provider,
            timestamp__date=report_date,
        ).count()
        success = RawSnapshot.objects.filter(
            provider=provider,
            timestamp__date=report_date,
            status_code=200,
            is_valid=True,
        ).count()
        success_rate = (success / total * 100) if total > 0 else 0
        
        provider_health[provider] = {
            'total_calls': total,
            'successful': success,
            'success_rate': success_rate,
        }
    
    report = DataQualityReport.objects.create(
        report_date=report_date,
        teams_synced=teams_synced,
        players_synced=players_synced,
        matches_synced=matches_synced,
        total_conflicts=total_conflicts,
        auto_resolved=auto_resolved,
        manual_review_needed=manual_review_needed,
        matches_with_complete_stats=matches_with_complete_stats,
        provider_health=provider_health,
    )
    
    logger.info(f"Generated data quality report for {report_date}")
    return report
