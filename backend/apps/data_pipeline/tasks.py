"""Data pipeline Celery tasks — syncs cricket data from APIs to PostgreSQL."""
import logging
from datetime import datetime
from typing import Any

import httpx
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from ml_engine.training import train_models_from_matches

from .normalizers import (
    NormalizedMatch,
    infer_category,
    merge_and_dedupe_matches,
    normalize_format,
    normalize_status,
    parse_date,
    normalize_cricapi_match,
    normalize_cricbuzz_live_match,
    normalize_cricbuzz_recent_match,
)

logger = logging.getLogger(__name__)


RAPIDAPI_ENDPOINTS = {
    'team_logo': '/cricket-teamlogo',
    'fixtures': {
        'all': '/cricket-schedule',
        'women': '/cricket-schedule-women',
        'league': '/cricket-schedule-league',
        'domestic': '/cricket-schedule-domestic',
        'international': '/cricket-schedule-international',
        'all_expanded': '/cricket-schedule-all',
    },
    'live_scores': '/cricket-livescores',
    'series': {
        'all': '/cricket-series',
        'women': '/cricket-series-women',
        'league': '/cricket-series-leagues',
        'domestic': '/cricket-series-domestic',
        'international': '/cricket-series-international',
    },
    'teams': {
        'international': '/cricket-teams',
        'women': '/cricket-teams-women',
        'league': '/cricket-teams-league',
        'domestic': '/cricket-teams-domestic',
    },
    'players_by_team': '/cricket-players?teamid={team_id}',
    'match_scoreboard': '/cricket-match-scoreboard?matchid={match_id}',
    'match_info': '/cricket-match-info?matchid={match_id}',
    'matches': {
        'upcoming': '/cricket-matches-upcoming',
        'recent': '/cricket-matches-recent',
        'live': '/cricket-matches-live',
    },
}


LEGACY_RAPIDAPI_ENDPOINTS = {
    'live_scores': '/matches/v1/live',
    'recent_matches': '/matches/v1/recent',
}


# ─────────────────────────────────────────────────
# CricAPI Client (ported from api_testing_web/app/api/cricapi.js)
# ─────────────────────────────────────────────────

def _cricapi_get(path: str, params: dict = None, health_key: str | None = None) -> dict:
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
        if health_key:
            _record_endpoint_success(health_key, 'cricapi', path)
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


def _rapidapi_get_with_fallback(paths: list[str], health_key: str | None = None) -> dict:
    """Try multiple RapidAPI paths until one succeeds."""
    last_error = None
    for path in paths:
        try:
            payload = _cricbuzz_get(path)
            if health_key:
                _record_endpoint_success(health_key, 'rapidapi', path)
            return payload
        except Exception as exc:  # pragma: no cover - defensive branch
            last_error = exc
            logger.warning('RapidAPI request failed for %s: %s', path, exc)
    if last_error:
        raise last_error
    return {}


def _extract_payload_items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ('data', 'response', 'matches', 'series', 'teams', 'players', 'results', 'list'):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]

    nested_data = payload.get('data')
    if isinstance(nested_data, dict):
        for key in ('matches', 'series', 'teams', 'players', 'results', 'list'):
            value = nested_data.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]

    return []


TTL_LIVE_SECONDS = 60
TTL_COMPLETED_SECONDS = 6 * 60 * 60
TTL_PLAYER_STATS_SECONDS = 24 * 60 * 60


def _record_endpoint_success(endpoint_key: str, provider: str, path: str) -> None:
    health = cache.get('pipeline:endpoint_health:last_success') or {}
    health[endpoint_key] = {
        'provider': provider,
        'path': path,
        'at': timezone.now().isoformat(),
    }
    cache.set('pipeline:endpoint_health:last_success', health, TTL_PLAYER_STATS_SECONDS)


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


def _normalize_rapidapi_match_row(row: dict, status_override: str | None = None) -> NormalizedMatch | None:
    info = row.get('matchInfo') if isinstance(row.get('matchInfo'), dict) else row
    if not isinstance(info, dict):
        return None

    team1_info = info.get('team1') if isinstance(info.get('team1'), dict) else {}
    team2_info = info.get('team2') if isinstance(info.get('team2'), dict) else {}

    team1 = str(team1_info.get('teamName') or info.get('team1_name') or info.get('team1') or 'Unknown')
    team2 = str(team2_info.get('teamName') or info.get('team2_name') or info.get('team2') or 'Unknown')
    series_name = str(info.get('seriesName') or info.get('series') or '')
    match_name = str(info.get('matchName') or info.get('name') or f'{team1} vs {team2}')

    status = status_override or normalize_status(info.get('status') or info.get('matchStatus'))
    fmt = normalize_format(info.get('matchFormat') or info.get('format') or info.get('matchType'))

    return NormalizedMatch(
        source='cricbuzz',
        source_id=str(info.get('matchId') or info.get('id') or info.get('matchid') or ''),
        name=match_name,
        series_name=series_name,
        team1_name=team1,
        team2_name=team2,
        format=fmt,
        status=status,
        category=infer_category(series_name=series_name, match_name=match_name, hint=str(info.get('matchType') or '')),
        match_date=parse_date(info.get('startDate') or info.get('date') or info.get('matchDate')),
        venue_name=str((info.get('venueInfo') or {}).get('ground') or info.get('venue') or ''),
        result_text=str(info.get('status') or info.get('result') or ''),
        raw_data=info,
    )


def _extract_rapidapi_matches(payload: dict, status: str) -> list[NormalizedMatch]:
    if isinstance(payload, dict) and isinstance(payload.get('typeMatches'), list):
        return _extract_cricbuzz_matches(payload, status=status)

    rows = []
    for row in _extract_payload_items(payload):
        normalized = _normalize_rapidapi_match_row(row, status_override=status)
        if normalized:
            rows.append(normalized)
    return rows


# ─────────────────────────────────────────────────
# Celery Tasks
# ─────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_current_matches(self):
    """Pull active/current matches from CricAPI → save to DB."""
    try:
        logger.info("Starting sync_current_matches task")
        data = _cricapi_get('/currentMatches', health_key='current_matches')
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
        data = _rapidapi_get_with_fallback([
            RAPIDAPI_ENDPOINTS['live_scores'],
            RAPIDAPI_ENDPOINTS['matches']['live'],
            LEGACY_RAPIDAPI_ENDPOINTS['live_scores'],
        ], health_key='live_scores')
        rows = _extract_rapidapi_matches(data, status='live')
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
        rows = []
        try:
            data = _cricapi_get('/series', health_key='series_all')
            rows = data.get('data', [])
        except Exception as cricapi_exc:
            logger.warning('sync_series: CricAPI failed, trying RapidAPI fallback: %s', cricapi_exc)

        if not rows:
            rapidapi_payload = _rapidapi_get_with_fallback([RAPIDAPI_ENDPOINTS['series']['all']], health_key='series_all')
            rows = _extract_payload_items(rapidapi_payload)

        synced = 0
        for row in rows:
            series_id = str(row.get('id') or row.get('seriesId') or row.get('series_id') or '')
            if not series_id:
                continue
            Series.objects.update_or_create(
                cricapi_id=series_id,
                defaults={
                    'name': row.get('name') or row.get('seriesName') or '',
                    'start_date': _parse_yyyy_mm_dd(row.get('startDate') or row.get('start_date') or row.get('start')),
                    'end_date': _parse_yyyy_mm_dd(row.get('endDate') or row.get('end_date') or row.get('end')),
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
        data = _rapidapi_get_with_fallback([
            RAPIDAPI_ENDPOINTS['matches']['recent'],
            LEGACY_RAPIDAPI_ENDPOINTS['recent_matches'],
        ], health_key='matches_recent')
        rows = _extract_rapidapi_matches(data, status='complete')
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


def _team_rows_from_payload(payload: dict) -> list[dict]:
    rows = _extract_payload_items(payload)
    if rows:
        return rows

    if isinstance(payload, dict) and isinstance(payload.get('teams'), list):
        return [row for row in payload['teams'] if isinstance(row, dict)]
    return []


def _player_rows_from_payload(payload: dict) -> list[dict]:
    rows = _extract_payload_items(payload)
    if rows:
        return rows

    if isinstance(payload, dict) and isinstance(payload.get('players'), list):
        return [row for row in payload['players'] if isinstance(row, dict)]
    return []


def _normalize_player_role(raw_role: str) -> str:
    role = str(raw_role or '').strip().lower().replace('-', '_').replace(' ', '_')
    if not role:
        return ''
    if 'keeper' in role:
        return 'wicket_keeper'
    if role in {'bat', 'batter'}:
        return 'batsman'
    if role in {'bowl', 'bowler'}:
        return 'bowler'
    if role in {'allrounder', 'all_rounder', 'allround'}:
        return 'all_rounder'
    return role if role in {'batsman', 'bowler', 'all_rounder', 'wicket_keeper'} else ''


def _extract_logo_rows(payload: dict) -> list[dict]:
    rows = _extract_payload_items(payload)
    if rows:
        return rows
    if isinstance(payload, dict) and isinstance(payload.get('logos'), list):
        return [row for row in payload['logos'] if isinstance(row, dict)]
    return []


def _row_name_value(row: dict) -> str:
    return str(
        row.get('teamName')
        or row.get('name')
        or row.get('team')
        or row.get('title')
        or ''
    ).strip()


def _row_logo_value(row: dict) -> str:
    return str(
        row.get('logo')
        or row.get('logoUrl')
        or row.get('logo_url')
        or row.get('image')
        or row.get('imageUrl')
        or row.get('teamLogo')
        or row.get('flag')
        or ''
    ).strip()


def _sync_team_logos_from_endpoint() -> int:
    from apps.matches.models import Team

    payload = _rapidapi_get_with_fallback([RAPIDAPI_ENDPOINTS['team_logo']], health_key='team_logo')
    rows = _extract_logo_rows(payload)
    updated = 0

    for row in rows:
        name = _row_name_value(row)
        logo_url = _row_logo_value(row)
        if not name or not logo_url:
            continue

        team = Team.objects.filter(name__iexact=name).first()
        if not team:
            continue

        if team.logo_url != logo_url:
            team.logo_url = logo_url
            team.save(update_fields=['logo_url'])
            updated += 1

    now_iso = timezone.now().isoformat()
    cache.set('pipeline:team_logos:last_sync_count', updated, TTL_PLAYER_STATS_SECONDS)
    cache.set('pipeline:team_logos:last_sync_at', now_iso, TTL_PLAYER_STATS_SECONDS)
    return updated


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
                payload = _cricapi_get('/match_scorecard', {'id': source_match_id}, health_key='match_scoreboard')
                rows = _iter_scorecard_rows(payload)
                if not rows:
                    scoreboard_payload = _rapidapi_get_with_fallback(
                        [RAPIDAPI_ENDPOINTS['match_scoreboard'].format(match_id=source_match_id)],
                        health_key='match_scoreboard',
                    )
                    rows = _iter_scorecard_rows(scoreboard_payload)
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


@shared_task(bind=True, max_retries=2, default_retry_delay=180)
def sync_rapidapi_teams(self):
    """Sync teams from RapidAPI category endpoints into Team records."""
    from apps.matches.models import Team

    try:
        synced = 0
        seen_names = set()

        for category in ('international', 'women', 'league', 'domestic'):
            path = RAPIDAPI_ENDPOINTS['teams'][category]
            payload = _rapidapi_get_with_fallback([path], health_key=f'teams_{category}')
            rows = _team_rows_from_payload(payload)

            for row in rows:
                name = str(row.get('teamName') or row.get('name') or '').strip()
                if not name:
                    continue

                dedupe_key = name.lower()
                if dedupe_key in seen_names:
                    continue

                seen_names.add(dedupe_key)
                Team.objects.update_or_create(
                    name=name,
                    defaults={
                        'short_name': str(row.get('shortName') or row.get('short_name') or '')[:10],
                        'country': str(row.get('country') or row.get('nation') or ''),
                        'logo_url': _row_logo_value(row),
                        'is_international': category in {'international', 'women'},
                    },
                )
                synced += 1

        logo_updates = _sync_team_logos_from_endpoint()

        now_iso = timezone.now().isoformat()
        cache.set('pipeline:teams:last_sync_count', synced, TTL_PLAYER_STATS_SECONDS)
        cache.set('pipeline:teams:last_sync_at', now_iso, TTL_PLAYER_STATS_SECONDS)
        logger.info('sync_rapidapi_teams: synced %s teams, updated %s logos', synced, logo_updates)
        return {'synced': synced, 'logos_updated': logo_updates}
    except Exception as exc:
        logger.error('sync_rapidapi_teams failed: %s', exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=180)
def sync_rapidapi_players(self, team_id: int | None = None):
    """Sync players from RapidAPI players endpoint for one team id or top local teams."""
    from apps.matches.models import Team
    from apps.players.models import Player

    try:
        if team_id is not None:
            team_ids = [int(team_id)]
        else:
            team_ids = list(Team.objects.values_list('id', flat=True)[:10])

        synced = 0
        failed = 0
        for source_team_id in team_ids:
            try:
                path = RAPIDAPI_ENDPOINTS['players_by_team'].format(team_id=source_team_id)
                payload = _rapidapi_get_with_fallback([path], health_key='players_by_team')
                rows = _player_rows_from_payload(payload)
                if not rows:
                    continue

                team_obj = Team.objects.filter(id=source_team_id).first()
                for row in rows:
                    player_id = str(row.get('id') or row.get('playerId') or row.get('pid') or '')
                    player_name = str(row.get('name') or row.get('playerName') or '').strip()
                    if not player_name:
                        continue

                    defaults = {
                        'full_name': str(row.get('fullName') or row.get('full_name') or player_name),
                        'country': str(row.get('country') or row.get('nationality') or ''),
                        'role': _normalize_player_role(str(row.get('role') or row.get('playerRole') or '')),
                        'batting_style': str(row.get('battingStyle') or row.get('batting_style') or ''),
                        'bowling_style': str(row.get('bowlingStyle') or row.get('bowling_style') or ''),
                        'image_url': str(row.get('image') or row.get('imageUrl') or row.get('playerImg') or ''),
                        'team': team_obj,
                        'raw_data': row,
                    }

                    if player_id:
                        Player.objects.update_or_create(cricapi_id=player_id, defaults={'name': player_name, **defaults})
                    else:
                        Player.objects.update_or_create(name=player_name, defaults=defaults)
                    synced += 1
            except Exception:
                failed += 1
                continue

        now_iso = timezone.now().isoformat()
        cache.set('pipeline:players:last_sync_count', synced, TTL_PLAYER_STATS_SECONDS)
        cache.set('pipeline:players:last_failed_count', failed, TTL_PLAYER_STATS_SECONDS)
        cache.set('pipeline:players:last_sync_at', now_iso, TTL_PLAYER_STATS_SECONDS)
        logger.info('sync_rapidapi_players: synced %s players (failed teams: %s)', synced, failed)
        return {'synced': synced, 'failed': failed}
    except Exception as exc:
        logger.error('sync_rapidapi_players failed: %s', exc)
        raise self.retry(exc=exc)


@shared_task
def sync_unified_matches():
    """Run cross-source sync and dedupe in one task, then persist normalized matches."""
    logger.info("Starting sync_unified_matches task")
    cricapi_rows = [normalize_cricapi_match(row) for row in _cricapi_get('/currentMatches').get('data', [])]
    cricbuzz_payload = _rapidapi_get_with_fallback([
        RAPIDAPI_ENDPOINTS['live_scores'],
        RAPIDAPI_ENDPOINTS['matches']['live'],
        LEGACY_RAPIDAPI_ENDPOINTS['live_scores'],
    ], health_key='live_scores')
    cricbuzz_rows = _extract_rapidapi_matches(cricbuzz_payload, status='live')
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


@shared_task(bind=True, max_retries=2, default_retry_delay=180)
def sync_rapidapi_team_logos(self):
    """Sync team logos from RapidAPI team logo endpoint."""
    try:
        updated = _sync_team_logos_from_endpoint()
        logger.info('sync_rapidapi_team_logos: updated %s team logos', updated)
        return {'updated': updated}
    except Exception as exc:
        logger.error('sync_rapidapi_team_logos failed: %s', exc)
        raise self.retry(exc=exc)
