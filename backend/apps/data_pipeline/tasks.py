"""Data pipeline Celery tasks — syncs cricket data from APIs to PostgreSQL."""
import logging
from datetime import datetime

import httpx
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from ml_engine.training import train_models_from_matches

from .normalizers import (
    merge_and_dedupe_matches,
    normalize_cricapi_match,
    normalize_cricbuzz_live_match,
    normalize_cricbuzz_recent_match,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────
# CricAPI Client (ported from api_testing_web/app/api/cricapi.js)
# ─────────────────────────────────────────────────

def _cricapi_get(path: str, params: dict = None) -> dict:
    """Generic CricAPI GET with error handling."""
    base_params = {'apikey': settings.CRICAPI_KEY, 'offset': '0'}
    if params:
        base_params.update(params)
    url = f"{settings.CRICAPI_BASE_URL}{path}"
    with httpx.Client(timeout=15) as client:
        response = client.get(url, params=base_params)
        response.raise_for_status()
        data = response.json()
        if data.get('status') and data['status'] != 'success':
            raise ValueError(f"CricAPI error: {data['status']}")
        return data


def _cricbuzz_get(path: str) -> dict:
    """Generic Cricbuzz (RapidAPI) GET with error handling."""
    url = f"{settings.CRICBUZZ_BASE_URL}{path}"
    headers = {
        'X-RapidAPI-Key': settings.CRICBUZZ_RAPIDAPI_KEY,
        'X-RapidAPI-Host': settings.CRICBUZZ_RAPIDAPI_HOST,
    }
    with httpx.Client(timeout=15) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


TTL_LIVE_SECONDS = 60
TTL_COMPLETED_SECONDS = 6 * 60 * 60
TTL_PLAYER_STATS_SECONDS = 24 * 60 * 60


def _parse_yyyy_mm_dd(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


def _upsert_match(normalized, status_override: str | None = None):
    from apps.matches.models import Match, Team, Venue

    team1_obj, _ = Team.objects.get_or_create(name=normalized.team1_name or 'Unknown')
    team2_obj, _ = Team.objects.get_or_create(name=normalized.team2_name or 'Unknown')

    venue_obj = None
    if normalized.venue_name:
        venue_obj, _ = Venue.objects.get_or_create(name=normalized.venue_name)

    defaults = {
        'name': normalized.name,
        'format': normalized.format,
        'category': normalized.category,
        'status': status_override or normalized.status,
        'team1': team1_obj,
        'team2': team2_obj,
        'venue': venue_obj,
        'match_date': _parse_yyyy_mm_dd(normalized.match_date),
        'result_text': normalized.result_text,
        'raw_data': normalized.raw_data,
    }

    lookup = {}
    if normalized.source_id:
        if 'cricapi' in normalized.sources:
            lookup['cricapi_id'] = normalized.source_id
        elif 'cricbuzz' in normalized.sources:
            lookup['cricbuzz_id'] = normalized.source_id

    if lookup:
        return Match.objects.update_or_create(defaults=defaults, **lookup)

    return Match.objects.update_or_create(
        name=normalized.name,
        match_date=defaults['match_date'],
        defaults=defaults,
    )


def _extract_cricbuzz_matches(payload: dict, status: str) -> list:
    normalized = []
    for type_match in payload.get('typeMatches', []):
        category_hint = str(type_match.get('matchType', '')).lower()
        for series_match in type_match.get('seriesMatches', []):
            wrapper = series_match.get('seriesAdWrapper', {})
            matches = series_match.get('matches', wrapper.get('matches', []))
            series_name = wrapper.get('seriesName', '')
            for match in matches:
                info = match.get('matchInfo', {})
                if not info:
                    continue
                if status == 'live':
                    normalized.append(
                        normalize_cricbuzz_live_match(info, category_hint=category_hint, series_name=series_name)
                    )
                else:
                    normalized.append(
                        normalize_cricbuzz_recent_match(info, category_hint=category_hint, series_name=series_name)
                    )
    return normalized


# ─────────────────────────────────────────────────
# Celery Tasks
# ─────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_current_matches(self):
    """Pull active/current matches from CricAPI → save to DB."""
    try:
        logger.info("Starting sync_current_matches task")
        data = _cricapi_get('/currentMatches')
        rows = [normalize_cricapi_match(row) for row in data.get('data', [])]
        synced = 0

        for row in rows:
            _upsert_match(row)
            synced += 1

        now_iso = timezone.now().isoformat()
        cache.set('pipeline:current_matches:last_sync_count', synced, TTL_LIVE_SECONDS)
        cache.set('pipeline:current_matches:last_sync_at', now_iso, TTL_LIVE_SECONDS)
        logger.info(f"sync_current_matches: synced {synced} matches")
        return {'synced': synced}

    except Exception as exc:
        logger.error(f"sync_current_matches failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def sync_cricbuzz_live(self):
    """Pull live matches from Cricbuzz RapidAPI → update DB."""
    try:
        logger.info("Starting sync_cricbuzz_live task")
        data = _cricbuzz_get('/matches/v1/live')
        rows = _extract_cricbuzz_matches(data, status='live')
        synced = 0

        for row in rows:
            _upsert_match(row, status_override='live')
            synced += 1

        now_iso = timezone.now().isoformat()
        cache.set('pipeline:live_matches:last_sync_count', synced, TTL_LIVE_SECONDS)
        cache.set('pipeline:live_matches:last_sync_at', now_iso, TTL_LIVE_SECONDS)
        logger.info(f"sync_cricbuzz_live: synced {synced} live matches")
        return {'synced': synced}

    except Exception as exc:
        logger.error(f"sync_cricbuzz_live failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2)
def sync_series(self):
    """Sync series list from CricAPI."""
    from apps.series.models import Series
    try:
        data = _cricapi_get('/series')
        rows = data.get('data', [])
        synced = 0
        for row in rows:
            series_id = str(row.get('id', ''))
            if not series_id:
                continue
            Series.objects.update_or_create(
                cricapi_id=series_id,
                defaults={
                    'name': row.get('name', ''),
                    'start_date': _parse_yyyy_mm_dd(row.get('startDate') or row.get('start_date')),
                    'end_date': _parse_yyyy_mm_dd(row.get('endDate') or row.get('end_date')),
                    'raw_data': row,
                }
            )
            synced += 1
        logger.info(f"sync_series: synced {synced} series")
        return {'synced': synced}
    except Exception as exc:
        logger.error(f"sync_series failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def sync_completed_matches(self):
    """Pull recently completed matches from Cricbuzz and update DB."""
    try:
        logger.info("Starting sync_completed_matches task")
        data = _cricbuzz_get('/matches/v1/recent')
        rows = _extract_cricbuzz_matches(data, status='complete')
        synced = 0
        for row in rows:
            _upsert_match(row, status_override='complete')
            synced += 1

        now_iso = timezone.now().isoformat()
        cache.set('pipeline:completed_matches:last_sync_count', synced, TTL_COMPLETED_SECONDS)
        cache.set('pipeline:completed_matches:last_sync_at', now_iso, TTL_COMPLETED_SECONDS)
        logger.info(f"sync_completed_matches: synced {synced} completed matches")
        return {'synced': synced}
    except Exception as exc:
        logger.error(f"sync_completed_matches failed: {exc}")
        raise self.retry(exc=exc)


def _iter_scorecard_rows(scorecard_data: dict) -> list[dict]:
    if not isinstance(scorecard_data, dict):
        return []
    for key in ('scorecard', 'scoreCard', 'data'):
        value = scorecard_data.get(key)
        if isinstance(value, list):
            return value
    if isinstance(scorecard_data.get('data'), dict):
        nested = scorecard_data['data'].get('scorecard') or scorecard_data['data'].get('scoreCard')
        if isinstance(nested, list):
            return nested
    return []


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def sync_player_stats(self, match_id: str | None = None):
    """Sync player-level scorecard stats for one match or recent completed matches."""
    from apps.matches.models import Match, MatchScorecard, Team
    from apps.players.models import Player, PlayerMatchStats

    try:
        logger.info("Starting sync_player_stats task")
        targets = []
        if match_id:
            targets = [str(match_id)]
        else:
            targets = list(
                Match.objects.filter(status='complete').exclude(cricapi_id='').values_list('cricapi_id', flat=True)[:20]
            )

        synced = 0
        failed = 0
        for source_match_id in targets:
            try:
                payload = _cricapi_get('/match_scorecard', {'id': source_match_id})
                rows = _iter_scorecard_rows(payload)
                if not rows:
                    continue

                match_obj = Match.objects.filter(cricapi_id=source_match_id).first()
                if not match_obj and source_match_id.isdigit():
                    match_obj = Match.objects.filter(id=int(source_match_id)).first()
                if not match_obj:
                    continue

                for innings_index, innings in enumerate(rows, start=1):
                    innings_num = innings.get('inningsNumber') or innings.get('inningsId') or innings_index
                    batting_team_name = innings.get('batTeamName') or innings.get('battingTeam') or ''
                    batting_team = None
                    if batting_team_name:
                        batting_team, _ = Team.objects.get_or_create(name=batting_team_name)

                    MatchScorecard.objects.update_or_create(
                        match=match_obj,
                        innings_number=int(innings_num),
                        defaults={
                            'batting_team': batting_team,
                            'total_runs': int(innings.get('score') or innings.get('runs') or 0),
                            'total_wickets': int(innings.get('wickets') or 0),
                            'total_overs': float(innings.get('overs') or 0),
                            'run_rate': float(innings.get('runRate') or 0),
                            'batting_data': innings.get('batting') or innings.get('batsmenData') or [],
                            'bowling_data': innings.get('bowling') or innings.get('bowlersData') or [],
                        },
                    )

                    for batter in innings.get('batting', []) or innings.get('batsmenData', []) or []:
                        batter_name = batter.get('batsmanName') or batter.get('name')
                        if not batter_name:
                            continue
                        player, _ = Player.objects.get_or_create(name=batter_name, defaults={'team': batting_team})
                        PlayerMatchStats.objects.update_or_create(
                            player=player,
                            match=match_obj,
                            innings_number=int(innings_num),
                            defaults={
                                'runs_scored': int(batter.get('runs') or 0),
                                'balls_faced': int(batter.get('balls') or 0),
                                'fours': int(batter.get('fours') or 0),
                                'sixes': int(batter.get('sixes') or 0),
                                'strike_rate': float(batter.get('strikeRate') or batter.get('sr') or 0),
                                'dismissed': str(batter.get('outDesc') or '').strip().lower() != 'not out',
                            },
                        )

                    for bowler in innings.get('bowling', []) or innings.get('bowlersData', []) or []:
                        bowler_name = bowler.get('bowlerName') or bowler.get('name')
                        if not bowler_name:
                            continue
                        player, _ = Player.objects.get_or_create(name=bowler_name)
                        PlayerMatchStats.objects.update_or_create(
                            player=player,
                            match=match_obj,
                            innings_number=int(innings_num),
                            defaults={
                                'overs_bowled': float(bowler.get('overs') or 0),
                                'runs_conceded': int(bowler.get('runs') or 0),
                                'wickets_taken': int(bowler.get('wickets') or 0),
                                'economy': float(bowler.get('economy') or 0),
                                'maidens': int(bowler.get('maidens') or 0),
                            },
                        )

                synced += 1
            except Exception as match_exc:
                failed += 1
                logger.warning(f"sync_player_stats: skipping match {source_match_id} due to error: {match_exc}")
                continue

        now_iso = timezone.now().isoformat()
        cache.set('pipeline:player_stats:last_sync_count', synced, TTL_PLAYER_STATS_SECONDS)
        cache.set('pipeline:player_stats:last_sync_at', now_iso, TTL_PLAYER_STATS_SECONDS)
        cache.set('pipeline:player_stats:last_failed_count', failed, TTL_PLAYER_STATS_SECONDS)
        logger.info(f"sync_player_stats: synced stats for {synced} matches (failed: {failed})")
        return {'synced': synced, 'failed': failed}
    except Exception as exc:
        logger.error(f"sync_player_stats failed: {exc}")
        raise self.retry(exc=exc)


@shared_task
def run_model_retraining_pipeline():
    """Train and persist the latest pre-match models from completed match history."""
    logger.info("run_model_retraining_pipeline triggered")
    summary = train_models_from_matches(settings.ML_MODEL_PATH, version=settings.ML_MODEL_VERSION)
    payload = {
        'version': summary.version,
        'sample_count': summary.sample_count,
        'model_type': summary.model_type,
        'accuracy': summary.accuracy,
        'auc_roc': summary.auc_roc,
        'brier_score': summary.brier_score,
    }
    cache.set('pipeline:model_retraining:last_result', payload, 24 * 60 * 60)
    cache.set('pipeline:model_retraining:last_run_at', timezone.now().isoformat(), 24 * 60 * 60)
    return payload


@shared_task
def sync_unified_matches():
    """Run cross-source sync and dedupe in one task, then persist normalized matches."""
    logger.info("Starting sync_unified_matches task")
    cricapi_rows = [normalize_cricapi_match(row) for row in _cricapi_get('/currentMatches').get('data', [])]
    cricbuzz_rows = _extract_cricbuzz_matches(_cricbuzz_get('/matches/v1/live'), status='live')
    merged = merge_and_dedupe_matches(cricapi_rows + cricbuzz_rows)

    synced = 0
    for row in merged:
        _upsert_match(row)
        synced += 1

    now_iso = timezone.now().isoformat()
    cache.set('pipeline:unified_matches:last_sync_count', synced, TTL_LIVE_SECONDS)
    cache.set('pipeline:unified_matches:last_sync_at', now_iso, TTL_LIVE_SECONDS)
    logger.info(f"sync_unified_matches: synced {synced} merged matches")
    return {'synced': synced}
