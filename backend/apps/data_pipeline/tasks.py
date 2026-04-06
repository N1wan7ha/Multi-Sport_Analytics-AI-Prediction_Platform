"""Data pipeline Celery tasks — syncs cricket data from APIs to PostgreSQL."""
import logging
from datetime import datetime
from time import perf_counter
from typing import Any
from urllib.parse import urlencode

import httpx
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db import models
from ml_engine.training import train_models_for_year_range, train_models_from_matches

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
from apps.data_quality.utils import (
    write_raw_snapshot,
    update_team_source,
    update_player_source,
    update_match_source,
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
    'schedules': {
        'all': '/cricket-schedule',
        'women': '/cricket-schedule-women',
        'league': '/cricket-schedule-league',
        'domestic': '/cricket-schedule-domestic',
        'international': '/cricket-schedule-international',
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
        'all': '/cricket-teams',
        'international': '/cricket-teams',
        'women': '/cricket-teams-women',
        'league': '/cricket-teams-league',
        'domestic': '/cricket-teams-domestic',
    },
    'players_by_team': '/cricket-players?teamid={team_id}',
    'players_list': '/cricket-players?teamid={team_id}',
    'match_scoreboard': '/cricket-match-scoreboard?matchid={match_id}',
    'match_info': '/cricket-match-info?matchid={match_id}',
    'matches': {
        'list': '/cricket-matches-upcoming',
        'upcoming': '/cricket-matches-upcoming',
        'recent': '/cricket-matches-recent',
        'live': '/cricket-matches-live',
    },
    'mcenter': {
        'scorecard': '/mcenter/v1/{match_id}/scard',
        'scorecard_v2': '/mcenter/v1/{match_id}/hscard',
        'overs': '/mcenter/v1/{match_id}/overs',
        'leanback': '/mcenter/v1/{match_id}/leanback',
    }
}

# CRICBUZZ WEB SOURCE
CRICBUZZ_LIVE_URL = 'https://www.cricbuzz.com/live-cricket-scores'
CRICBUZZ_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


LEGACY_RAPIDAPI_ENDPOINTS = {
    'live_scores': '/matches/v1/live',
    'upcoming_matches': '/matches/v1/upcoming',
    'recent_matches': '/matches/v1/recent',
    'players_trending': '/stats/v1/player/trending',
}

LIVESCORE6_ENDPOINTS = {
    'live_scores': '/matches/v2/list-live?Category=cricket',
}

APILAYER_ENDPOINTS = {
    'sports': '/sports',
    'affiliates': '/affiliates',
}


# ─────────────────────────────────────────────────
# CricAPI Client (ported from api_testing_web/app/api/cricapi.js)
# ─────────────────────────────────────────────────

def _safe_write_raw_snapshot(
    provider: str,
    endpoint: str,
    payload: dict,
    *,
    status_code: int,
    response_time_ms: int | None = None,
    request_params: dict | None = None,
    is_valid: bool = True,
    error_message: str = '',
) -> None:
    """Persist raw payload in Bronze layer without breaking sync on write failures."""
    try:
        write_raw_snapshot(
            provider=provider,
            endpoint=(endpoint or '')[:50],
            payload=payload if isinstance(payload, dict) else {'raw': payload},
            status_code=status_code,
            response_time_ms=response_time_ms,
            request_params=request_params or {},
            is_valid=is_valid,
            error_message=error_message,
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning('Raw snapshot write failed provider=%s endpoint=%s: %s', provider, endpoint, exc)


def _cricapi_get(path: str, params: dict = None, health_key: str | None = None) -> dict:
    """Generic CricAPI GET with error handling."""
    base_params = {'apikey': settings.CRICAPI_KEY, 'offset': '0'}
    if params:
        base_params.update(params)
    url = f"{settings.CRICAPI_BASE_URL}{path}"
    start = perf_counter()
    with httpx.Client(timeout=15) as client:
        response = client.get(url, params=base_params)
        response.raise_for_status()
        data = response.json()
        elapsed_ms = int((perf_counter() - start) * 1000)
        _safe_write_raw_snapshot(
            provider='cricapi',
            endpoint=path,
            payload=data,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            request_params=base_params,
        )
        if data.get('status') and data['status'] != 'success':
            raise ValueError(f"CricAPI error: {data['status']}")
        if health_key:
            _record_endpoint_success(health_key, 'cricapi', path)
        return data


def _rapidapi_get(path: str, *, base_url: str, host: str, api_key: str, provider: str) -> dict:
    """Generic RapidAPI GET with configurable provider settings."""
    url = f"{base_url}{path}"
    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': host,
    }
    start = perf_counter()
    with httpx.Client(timeout=15) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
        elapsed_ms = int((perf_counter() - start) * 1000)
        _safe_write_raw_snapshot(
            provider=provider,
            endpoint=path,
            payload=payload,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
        )
        return payload


def _rapidapi_free_get(path: str) -> dict:
    return _rapidapi_get(
        path,
        base_url=settings.RAPIDAPI_FREE_BASE_URL,
        host=settings.RAPIDAPI_FREE_HOST,
        api_key=settings.RAPIDAPI_FREE_KEY,
        provider='rapidapi_free',
    )


def _cricbuzz_get(path: str) -> dict:
    return _rapidapi_get(
        path,
        base_url=settings.CRICBUZZ_BASE_URL,
        host=settings.CRICBUZZ_RAPIDAPI_HOST,
        api_key=settings.CRICBUZZ_RAPIDAPI_KEY,
        provider='cricbuzz2',
    )


def _livescore6_get(path: str) -> dict:
    return _rapidapi_get(
        path,
        base_url=settings.LIVESCORE6_BASE_URL,
        host=settings.LIVESCORE6_RAPIDAPI_HOST,
        api_key=settings.LIVESCORE6_RAPIDAPI_KEY,
        provider='livescore6',
    )


def _cricket_livescore_get(path: str) -> dict:
    return _rapidapi_get(
        path,
        base_url=settings.CRICKET_LIVESCORE_URL,
        host=settings.CRICKET_LIVESCORE_HOST,
        api_key=settings.RAPIDAPI_FREE_KEY,
        provider='rapidapi_livescore_free',
    )


def _live_score_cricket_get(path: str) -> dict:
    return _rapidapi_get(
        path,
        base_url=settings.LIVE_SCORE_CRICKET_URL,
        host=settings.LIVE_SCORE_CRICKET_HOST,
        api_key=settings.RAPIDAPI_FREE_KEY,
        provider='rapidapi_score_cricket',
    )


def _rapidapi_provider_order(path: str) -> list[str]:
    normalized = str(path or '').strip().lower()

    # livescore6 host serves `/matches/v2/*` endpoints.
    if normalized.startswith('/matches/v2/'):
        return ['rapidapi_livescore6']

    # cricket-api-free-data host serves `/cricket-*` catalog endpoints.
    if normalized.startswith('/cricket-'):
        return ['rapidapi_free', 'rapidapi_cricbuzz2', 'rapidapi_livescore_free', 'rapidapi_score_cricket']

    # cricbuzz-cricket2 host serves `/matches/v1/*`, `/series/v1/*`, etc.
    if normalized.startswith('/matches/') or normalized.startswith('/mcenter/') or normalized.startswith('/series/') or normalized.startswith('/teams/') or normalized.startswith('/stats/') or normalized.startswith('/news/') or normalized.startswith('/photos/') or normalized.startswith('/venues/'):
        return ['rapidapi_cricbuzz2', 'rapidapi_free', 'rapidapi_livescore_free']

    return ['rapidapi_free', 'rapidapi_cricbuzz2', 'rapidapi_livescore_free']


def _apilayer_get(path: str, *, base_url: str, params: dict[str, Any] | None = None) -> dict:
    """Generic APILayer GET with API key header and Bronze-layer snapshot persistence."""
    api_key = str(getattr(settings, 'APILAYER_API_KEY', '') or '').strip()
    if not api_key:
        raise ValueError('APILAYER_API_KEY is not configured')

    clean_base = str(base_url or '').rstrip('/')
    clean_path = f"/{str(path or '').lstrip('/')}"
    endpoint = clean_path
    if params:
        endpoint = f"{clean_path}?{urlencode(params, doseq=True)}"

    url = f"{clean_base}{clean_path}"
    headers = {
        'apikey': api_key,
    }

    timeout_seconds = float(getattr(settings, 'APILAYER_TIMEOUT_SECONDS', 30) or 30)

    with httpx.Client(timeout=httpx.Timeout(timeout_seconds, connect=10.0)) as client:
        last_exc = None
        for attempt in range(1, 3):
            start = perf_counter()
            try:
                response = client.get(url, headers=headers, params=params or None)
                response.raise_for_status()

                try:
                    payload = response.json()
                except Exception:
                    payload = {'raw_text': response.text}

                elapsed_ms = int((perf_counter() - start) * 1000)
                _safe_write_raw_snapshot(
                    provider='apilayer_odds',
                    endpoint=endpoint,
                    payload=payload if isinstance(payload, dict) else {'data': payload},
                    status_code=response.status_code,
                    response_time_ms=elapsed_ms,
                    request_params=params or {},
                )
                return payload
            except (httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                last_exc = exc
                if attempt == 1:
                    logger.warning('APILayer timeout on %s, retrying once: %s', endpoint, exc)
                    continue
                raise

        if last_exc:
            raise last_exc
        raise RuntimeError(f'APILayer request failed without explicit exception: {endpoint}')


def _extract_apilayer_rows(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ('data', 'response', 'results', 'sports', 'affiliates', 'items', 'list'):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]

    return []


def _apilayer_payload_shape(payload: Any) -> dict[str, Any]:
    """Return a compact payload fingerprint for debugging schema drift."""
    if isinstance(payload, list):
        return {
            'type': 'list',
            'length': len(payload),
            'first_item_keys': sorted(list(payload[0].keys()))[:15] if payload and isinstance(payload[0], dict) else [],
        }
    if isinstance(payload, dict):
        return {
            'type': 'dict',
            'keys': sorted(list(payload.keys()))[:20],
        }
    return {
        'type': type(payload).__name__,
    }


def _row_mentions_sport(row: dict[str, Any], sport: str) -> bool:
    needle = str(sport or '').strip().lower()
    if not needle:
        return False

    candidate_parts = [
        row.get('name'),
        row.get('title'),
        row.get('sport'),
        row.get('slug'),
        row.get('key'),
        row.get('description'),
        row.get('category'),
        row.get('group'),
    ]
    haystack = ' '.join(str(part or '').strip().lower() for part in candidate_parts)
    return needle in haystack


def _rapidapi_get_with_fallback(
    paths: list[str],
    health_key: str | None = None,
    return_meta: bool = False,
) -> dict | tuple[dict, str, str]:
    """Try multiple RapidAPI paths and providers until one succeeds."""
    last_error = None
    for path in paths:
        for provider in _rapidapi_provider_order(path):
            try:
                if provider == 'rapidapi_free':
                    payload = _rapidapi_free_get(path)
                elif provider == 'rapidapi_livescore6':
                    payload = _livescore6_get(path)
                elif provider == 'rapidapi_livescore_free':
                    payload = _cricket_livescore_get(path)
                elif provider == 'rapidapi_score_cricket':
                    payload = _live_score_cricket_get(path)
                else:
                    payload = _cricbuzz_get(path)

                if health_key:
                    _record_endpoint_success(health_key, provider, path)
                if return_meta:
                    return payload, provider, path
                return payload
            except Exception as exc:  # pragma: no cover - defensive branch
                last_error = exc
                logger.warning('RapidAPI request failed for provider=%s path=%s: %s', provider, path, exc)

    if last_error:
        raise last_error
    if return_meta:
        return {}, '', ''
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
ENDPOINT_HEALTH_HISTORY_LIMIT = 24


ENDPOINT_HEALTH_LAST_SUCCESS_CACHE_KEY = 'pipeline:endpoint_health:last_success'
ENDPOINT_HEALTH_HISTORY_CACHE_KEY = 'pipeline:endpoint_health:history'


def _record_endpoint_success(endpoint_key: str, provider: str, path: str) -> None:
    event = {
        'provider': provider,
        'path': path,
        'at': timezone.now().isoformat(),
    }

    health = cache.get(ENDPOINT_HEALTH_LAST_SUCCESS_CACHE_KEY) or {}
    health[endpoint_key] = event
    cache.set(ENDPOINT_HEALTH_LAST_SUCCESS_CACHE_KEY, health, TTL_PLAYER_STATS_SECONDS)

    history = cache.get(ENDPOINT_HEALTH_HISTORY_CACHE_KEY) or {}
    endpoint_history = history.get(endpoint_key)
    if not isinstance(endpoint_history, list):
        endpoint_history = []

    endpoint_history.append(event)
    history[endpoint_key] = endpoint_history[-ENDPOINT_HEALTH_HISTORY_LIMIT:]
    cache.set(ENDPOINT_HEALTH_HISTORY_CACHE_KEY, history, TTL_PLAYER_STATS_SECONDS)


def _parse_yyyy_mm_dd(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


def _upsert_match(
    normalized,
    status_override: str | None = None,
    source_provider: str | None = None,
    raw_snapshot_id: int | None = None,
):
    from apps.matches.models import Match, Team, Venue

    team1_obj, _ = Team.objects.get_or_create(name=normalized.team1_name or 'Unknown')
    team2_obj, _ = Team.objects.get_or_create(name=normalized.team2_name or 'Unknown')

    venue_obj = None
    if normalized.venue_name:
        venue_obj, _ = Venue.objects.get_or_create(name=normalized.venue_name)

    # Link to Series if possible
    series_obj = None
    if normalized.series_name:
        from apps.series.models import Series
        series_obj = Series.objects.filter(name__icontains=normalized.series_name).first()

    provider = source_provider or ('cricapi' if 'cricapi' in (normalized.sources or []) else 'cricbuzz2')
    base_confidence = 80 if provider == 'cricbuzz2' else 75

    defaults = {
        'name': normalized.name,
        'format': normalized.format,
        'category': normalized.category,
        'status': status_override or normalized.status,
        'team1': team1_obj,
        'team2': team2_obj,
        'venue': venue_obj,
        'series': series_obj,
        'series_name': normalized.series_name or (series_obj.name if series_obj else ''),
        'match_date': _parse_yyyy_mm_dd(normalized.match_date),
        'result_text': normalized.result_text,
        'raw_data': normalized.raw_data,
        'primary_source': provider,
        'confidence_score': base_confidence,
        'source_urls': [
            {
                'provider': provider,
                'timestamp': timezone.now().isoformat(),
            }
        ],
    }

    lookup = {}
    if normalized.source_id:
        if 'cricapi' in normalized.sources:
            lookup['cricapi_id'] = normalized.source_id
        elif 'cricbuzz' in normalized.sources:
            lookup['cricbuzz_id'] = normalized.source_id

    if lookup:
        match_obj, created = Match.objects.update_or_create(defaults=defaults, **lookup)
    else:
        match_obj, created = Match.objects.update_or_create(
            name=normalized.name,
            match_date=defaults['match_date'],
            defaults=defaults,
        )

    # Field-level lineage and conflict handling.
    update_match_source(
        match_obj,
        field_name='name',
        value=normalized.name,
        provider=provider,
        confidence_score=base_confidence,
        raw_snapshot_id=raw_snapshot_id,
    )
    update_match_source(
        match_obj,
        field_name='status',
        value=(status_override or normalized.status),
        provider=provider,
        confidence_score=base_confidence,
        raw_snapshot_id=raw_snapshot_id,
    )
    if normalized.result_text:
        update_match_source(
            match_obj,
            field_name='result_text',
            value=normalized.result_text,
            provider=provider,
            confidence_score=base_confidence,
            raw_snapshot_id=raw_snapshot_id,
        )
    match_obj.save()
    return match_obj, created


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
                    # Some "live" endpoints also include completed fixtures.
                    resolved_status = normalize_status(
                        info.get('state') or info.get('status') or info.get('stateTitle')
                    )
                    if resolved_status != 'live':
                        continue
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


def _extract_livescore_team_name(raw_team: Any) -> str:
    if isinstance(raw_team, list) and raw_team:
        raw_team = raw_team[0]

    if isinstance(raw_team, dict):
        for key in ('Nm', 'Name', 'name', 'teamName', 'Tnm', 'Snm', 'Abr'):
            value = raw_team.get(key)
            if value:
                return str(value).strip()

    if raw_team:
        return str(raw_team).strip()

    return 'Unknown'


def _normalize_livescore6_event(
    event: dict[str, Any],
    *,
    stage: dict[str, Any] | None = None,
    status_override: str | None = None,
) -> NormalizedMatch | None:
    stage = stage or {}

    team1 = _extract_livescore_team_name(event.get('T1') or event.get('team1') or event.get('home'))
    team2 = _extract_livescore_team_name(event.get('T2') or event.get('team2') or event.get('away'))
    if team1 == 'Unknown' and team2 == 'Unknown':
        return None

    series_name = str(
        stage.get('Snm')
        or stage.get('Cnm')
        or event.get('Cnm')
        or event.get('CompN')
        or ''
    )
    match_name = str(event.get('Nm') or event.get('EtTx') or f'{team1} vs {team2}')

    resolved_status = status_override or normalize_status(event.get('Eps') or event.get('status') or event.get('Esm'))
    if status_override == 'live':
        resolved_status = 'live'

    format_hint = event.get('Trp') or event.get('matchFormat') or event.get('EtTx')

    return NormalizedMatch(
        source='livescore6',
        source_id=str(event.get('Eid') or event.get('id') or ''),
        name=match_name,
        series_name=series_name,
        team1_name=team1,
        team2_name=team2,
        format=normalize_format(format_hint),
        status=resolved_status,
        category=infer_category(
            series_name=series_name,
            match_name=match_name,
            hint=str(stage.get('CompD') or event.get('CompD') or ''),
        ),
        match_date=parse_date(event.get('Esd') or event.get('Edt') or event.get('date')),
        venue_name=str(event.get('Vnm') or event.get('venue') or ''),
        result_text=str(event.get('Eps') or event.get('status') or ''),
        raw_data={'stage': stage, 'event': event},
    )


def _extract_livescore6_matches(payload: dict[str, Any], status: str) -> list[NormalizedMatch]:
    rows: list[NormalizedMatch] = []
    if not isinstance(payload, dict):
        return rows

    stages = payload.get('Stages') or payload.get('stages')
    if not isinstance(stages, list):
        stages = []

    for stage in stages:
        if not isinstance(stage, dict):
            continue
        events = stage.get('Events') or stage.get('events') or []
        if not isinstance(events, list):
            continue

        for event in events:
            if not isinstance(event, dict):
                continue
            normalized = _normalize_livescore6_event(event, stage=stage, status_override=status)
            if normalized:
                rows.append(normalized)

    if rows:
        return rows

    # Some responses can have events at root-level.
    root_events = payload.get('Events') or payload.get('events') or []
    if isinstance(root_events, list):
        for event in root_events:
            if not isinstance(event, dict):
                continue
            normalized = _normalize_livescore6_event(event, stage=None, status_override=status)
            if normalized:
                rows.append(normalized)

    return rows


def _extract_rapidapi_matches(payload: dict, status: str) -> list[NormalizedMatch]:
    if isinstance(payload, dict) and (
        isinstance(payload.get('Stages'), list) or isinstance(payload.get('stages'), list)
    ):
        return _extract_livescore6_matches(payload, status=status)

    if isinstance(payload, dict) and isinstance(payload.get('typeMatches'), list):
        return _extract_cricbuzz_matches(payload, status=status)

    rows = []
    for row in _extract_payload_items(payload):
        normalized = _normalize_rapidapi_match_row(row, status_override=status)
        if normalized:
            rows.append(normalized)
    return rows


def _extract_live_rows_with_fallback(paths: list[str]) -> tuple[list[NormalizedMatch], str, str]:
    """Fetch live rows by trying endpoints until one returns non-empty normalized rows."""
    last_error = None

    for path in paths:
        try:
            payload, provider, resolved_path = _rapidapi_get_with_fallback(
                [path],
                health_key='live_scores',
                return_meta=True,
            )
            rows = _extract_rapidapi_matches(payload, status='live')
            if rows:
                return rows, (provider or ''), (resolved_path or path)

            logger.info('Live endpoint returned no normalized rows: provider=%s path=%s', provider, resolved_path or path)
        except Exception as exc:  # pragma: no cover - defensive branch
            last_error = exc
            logger.warning('Live endpoint fetch failed for path=%s: %s', path, exc)

    if last_error:
        raise last_error

    return [], '', ''


# ─────────────────────────────────────────────────
# Celery Tasks
# ─────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_current_matches(self):
    """Pull active/current matches from CricAPI → save to DB."""
    try:
        logger.info("Starting sync_current_matches task")
        try:
            data = _cricapi_get('/currentMatches', health_key='current_matches')
            rows = [normalize_cricapi_match(row) for row in data.get('data', [])]
        except Exception as cric_err:
            logger.warning(f"CricAPI failed in sync_current_matches, falling back to RapidAPI: {cric_err}")
            paths = [
                RAPIDAPI_ENDPOINTS['live_scores'],
                RAPIDAPI_ENDPOINTS['matches']['live'],
                LEGACY_RAPIDAPI_ENDPOINTS['live_scores'],
                LIVESCORE6_ENDPOINTS['live_scores'],
            ]
            rows, fallback_provider, _ = _extract_live_rows_with_fallback(paths)
            logger.info(f"RapidAPI fallback retrieved {len(rows)} live rows using {fallback_provider}")

        # Supplement upcoming fixtures from RapidAPI so UI filters have consistent data.
        upcoming_payload, upcoming_provider, _ = _rapidapi_get_with_fallback([
            RAPIDAPI_ENDPOINTS['matches']['upcoming'],
            LEGACY_RAPIDAPI_ENDPOINTS['upcoming_matches'],
        ], health_key='matches_upcoming', return_meta=True)
        rows.extend(_extract_rapidapi_matches(upcoming_payload, status='upcoming'))

        rows = merge_and_dedupe_matches(rows)
        synced = 0

        for row in rows:
            source_provider = 'cricapi' if row.source == 'cricapi' else (upcoming_provider or 'cricbuzz2')
            _upsert_match(row, source_provider=source_provider)
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
        rows, provider, resolved_path = _extract_live_rows_with_fallback([
            RAPIDAPI_ENDPOINTS['live_scores'],
            RAPIDAPI_ENDPOINTS['matches']['live'],
            LEGACY_RAPIDAPI_ENDPOINTS['live_scores'],
            LIVESCORE6_ENDPOINTS['live_scores'],
        ])

        if not rows:
            logger.warning('sync_cricbuzz_live: no live rows found across all endpoints')

        synced = 0

        for row in rows:
            _upsert_match(row, status_override='live', source_provider=(provider or 'cricbuzz2'))
            synced += 1

        now_iso = timezone.now().isoformat()
        cache.set('pipeline:live_matches:last_sync_count', synced, TTL_LIVE_SECONDS)
        cache.set('pipeline:live_matches:last_sync_at', now_iso, TTL_LIVE_SECONDS)
        logger.info('sync_cricbuzz_live: synced %s live matches (provider=%s path=%s)', synced, provider or 'n/a', resolved_path or 'n/a')
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


@shared_task(bind=True, max_retries=2, default_retry_delay=180)
def sync_apilayer_catalog(self, sport: str | None = None):
    """Sync APILayer catalog data and keep cricket-focused subsets for the current platform scope."""
    try:
        configured_sport = str(getattr(settings, 'APILAYER_PRIMARY_SPORT', 'cricket') or 'cricket')
        target_sport = str(sport or configured_sport).strip().lower() or 'cricket'

        if target_sport != 'cricket':
            logger.info('sync_apilayer_catalog requested sport=%s (current product scope remains cricket-first)', target_sport)

        api_key = str(getattr(settings, 'APILAYER_API_KEY', '') or '').strip()
        if not api_key:
            summary = {
                'status': 'skipped',
                'reason': 'APILAYER_API_KEY not configured',
                'sport': target_sport,
                'sports_total': 0,
                'sports_filtered': 0,
                'affiliates_total': 0,
            }
            cache.set('pipeline:apilayer:last_sync_result', summary, TTL_PLAYER_STATS_SECONDS)
            cache.set('pipeline:apilayer:last_sync_at', timezone.now().isoformat(), TTL_PLAYER_STATS_SECONDS)
            return summary

        try:
            sports_payload = _apilayer_get(
                APILAYER_ENDPOINTS['sports'],
                base_url=settings.APILAYER_ODDS_BASE_URL,
                params={'all': 'true'},
            )
            sports_shape = _apilayer_payload_shape(sports_payload)
            sports_rows = _extract_apilayer_rows(sports_payload)
            filtered_rows = [row for row in sports_rows if _row_mentions_sport(row, target_sport)]
            _record_endpoint_success('apilayer_sports', 'apilayer_odds', APILAYER_ENDPOINTS['sports'])

            if not sports_rows:
                logger.warning(
                    'sync_apilayer_catalog: sports payload had no extractable rows; shape=%s',
                    sports_shape,
                )

            affiliates_payload = _apilayer_get(
                APILAYER_ENDPOINTS['affiliates'],
                base_url=settings.APILAYER_THERUNDOWN_BASE_URL,
            )
            affiliates_shape = _apilayer_payload_shape(affiliates_payload)
            affiliate_rows = _extract_apilayer_rows(affiliates_payload)
            _record_endpoint_success('apilayer_affiliates', 'apilayer_odds', APILAYER_ENDPOINTS['affiliates'])

            if not affiliate_rows:
                logger.warning(
                    'sync_apilayer_catalog: affiliates payload had no extractable rows; shape=%s',
                    affiliates_shape,
                )
        except (httpx.ReadTimeout, httpx.ConnectTimeout) as timeout_exc:
            now_iso = timezone.now().isoformat()
            summary = {
                'status': 'degraded',
                'reason': f'apilayer timeout: {timeout_exc}',
                'sport': target_sport,
                'sports_total': 0,
                'sports_filtered': 0,
                'affiliates_total': 0,
            }
            cache.set('pipeline:apilayer:last_sync_result', summary, TTL_PLAYER_STATS_SECONDS)
            cache.set('pipeline:apilayer:last_sync_at', now_iso, TTL_PLAYER_STATS_SECONDS)
            logger.warning('sync_apilayer_catalog degraded due to timeout: %s', timeout_exc)
            return summary
        except httpx.HTTPStatusError as status_exc:
            status_code = int(getattr(status_exc.response, 'status_code', 0) or 0)
            if status_code >= 500:
                now_iso = timezone.now().isoformat()
                summary = {
                    'status': 'degraded',
                    'reason': f'apilayer upstream error {status_code}',
                    'sport': target_sport,
                    'sports_total': 0,
                    'sports_filtered': 0,
                    'affiliates_total': 0,
                }
                cache.set('pipeline:apilayer:last_sync_result', summary, TTL_PLAYER_STATS_SECONDS)
                cache.set('pipeline:apilayer:last_sync_at', now_iso, TTL_PLAYER_STATS_SECONDS)
                logger.warning('sync_apilayer_catalog degraded due to HTTP %s: %s', status_code, status_exc)
                return summary
            raise

        now_iso = timezone.now().isoformat()
        summary = {
            'status': 'ok',
            'sport': target_sport,
            'sports_total': len(sports_rows),
            'sports_filtered': len(filtered_rows),
            'affiliates_total': len(affiliate_rows),
            'sports_payload_shape': sports_shape,
            'affiliates_payload_shape': affiliates_shape,
        }

        cache.set('pipeline:apilayer:last_sync_result', summary, TTL_PLAYER_STATS_SECONDS)
        cache.set('pipeline:apilayer:last_sync_at', now_iso, TTL_PLAYER_STATS_SECONDS)
        cache.set('pipeline:apilayer:sports_filtered', filtered_rows[:200], TTL_PLAYER_STATS_SECONDS)
        cache.set('pipeline:apilayer:affiliates', affiliate_rows[:200], TTL_PLAYER_STATS_SECONDS)

        logger.info(
            'sync_apilayer_catalog: sports_total=%s sports_filtered=%s affiliates=%s sport=%s',
            summary['sports_total'],
            summary['sports_filtered'],
            summary['affiliates_total'],
            target_sport,
        )
        return summary
    except Exception as exc:
        logger.error('sync_apilayer_catalog failed: %s', exc)
        raise self.retry(exc=exc)


@shared_task
def run_data_quality_report_pipeline():
    """Generate and cache the daily data quality report snapshot."""
    from apps.data_quality.utils import generate_data_quality_report

    report = generate_data_quality_report()
    payload = {
        'report_date': report.report_date.isoformat(),
        'teams_synced': int(report.teams_synced),
        'players_synced': int(report.players_synced),
        'matches_synced': int(report.matches_synced),
        'total_conflicts': int(report.total_conflicts),
        'manual_review_needed': int(report.manual_review_needed),
        'matches_with_complete_stats': int(report.matches_with_complete_stats),
        'provider_health': report.provider_health,
    }
    cache.set('pipeline:data_quality:last_result', payload, 24 * 60 * 60)
    cache.set('pipeline:data_quality:last_run_at', timezone.now().isoformat(), 24 * 60 * 60)
    logger.info('run_data_quality_report_pipeline: report_date=%s', payload['report_date'])
    return payload


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def sync_completed_matches(self):
    """Pull recently completed matches from Cricbuzz and update DB."""
    try:
        logger.info("Starting sync_completed_matches task")
        data, provider, _ = _rapidapi_get_with_fallback([
            RAPIDAPI_ENDPOINTS['matches']['recent'],
            LEGACY_RAPIDAPI_ENDPOINTS['recent_matches'],
        ], health_key='matches_recent', return_meta=True)
        rows = _extract_rapidapi_matches(data, status='complete')
        synced = 0
        for row in rows:
            _upsert_match(row, status_override='complete', source_provider=(provider or 'cricbuzz2'))
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
    
    # Try common list keys
    for key in ('scorecard', 'scoreCard', 'matchScorecard', 'matchScoreCard', 'innings', 'data', 'score_card'):
        value = scorecard_data.get(key)
        if isinstance(value, list):
            return value
            
    # Try nested data
    res = scorecard_data.get('response') or scorecard_data.get('data')
    if isinstance(res, dict):
        # Handle dict with innings keys
        if 'firstInnings' in res or 'secondInnings' in res:
            innings_list = []
            for i, key in enumerate(['firstInnings', 'secondInnings', 'thirdInnings', 'fourthInnings'], 1):
                if res.get(key):
                    row = res[key]
                    if not row.get('inningsNumber'):
                        row['inningsNumber'] = i
                    innings_list.append(row)
            return innings_list

        for key in ('scorecard', 'scoreCard', 'matchScorecard', 'matchScoreCard', 'innings', 'score_card'):
            val = res.get(key)
            if isinstance(val, list):
                return val
                
    # Try even deeper (some RapidAPIs nest heavily)
    for key in scorecard_data.keys():
        if isinstance(scorecard_data[key], dict):
            for subkey in ('scorecard', 'scoreCard', 'innings'):
                if isinstance(scorecard_data[key].get(subkey), list):
                    return scorecard_data[key][subkey]

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

    payload, provider, _ = _rapidapi_get_with_fallback(
        [RAPIDAPI_ENDPOINTS['team_logo']],
        health_key='team_logo',
        return_meta=True,
    )
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
            update_team_source(
                team,
                field_name='logo_url',
                value=logo_url,
                provider=(provider or 'rapidapi_free'),
                confidence_score=65,
            )
            team.save(update_fields=['logo_url', 'primary_source', 'confidence_score', 'source_urls'])
            updated += 1

    now_iso = timezone.now().isoformat()
    cache.set('pipeline:team_logos:last_sync_count', updated, TTL_PLAYER_STATS_SECONDS)
    cache.set('pipeline:team_logos:last_sync_at', now_iso, TTL_PLAYER_STATS_SECONDS)
    return updated


def _scrape_cricbuzz_livescores() -> list[NormalizedMatch]:
    """Fallback scrape from Cricbuzz Web UI for ultra-accurate status updates."""
    from .normalizers import NormalizedMatch, normalize_status, normalize_format
    import re
    
    rows = []
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(CRICBUZZ_LIVE_URL, headers=CRICBUZZ_HEADERS)
            if resp.status_code != 200:
                logger.debug(f"Cricbuzz Web Scrape failed: HTTP {resp.status_code}")
                return []
            
            html = resp.text
            
            # Extract Series Context (Headers appear before match cards)
            # Pattern: <h2 class="cb-lv-grps-hdr">(.*?)</h2>
            series_titles = re.findall(r'<h2 class="cb-lv-grps-hdr">(.*?)</h2>', html)
            
            # Split by series header to associate matches with their series
            series_split = re.split(r'<h2 class="cb-lv-grps-hdr">', html)
            
            for index, group in enumerate(series_split):
                if index == 0: continue # Headerless preamble
                
                current_series_name = ''
                header_match = re.search(r'^(.*?)</h2>', group)
                if header_match:
                    current_series_name = header_match.group(1).replace('Scorecard', '').strip()
                
                # Split this series group by match card indicators
                blocks = re.split(r'cb-lv-scrs-col', group)
                for i in range(1, len(blocks)):
                    prev_chunk = blocks[i-1]
                    status_chunk = blocks[i]
                    
                    # Extract Cricbuzz ID and Match Name
                    id_match = re.search(r'href="(?:https?://[^/]+)?/(?:live-cricket-scores|cricket-match/[^/]+)/(\d+)/([^"]+)"[^>]*>(.*?)</a>', prev_chunk)
                    if not id_match:
                        continue
                        
                    cb_id = id_match.group(1)
                    slug = id_match.group(2)
                    title = id_match.group(3).strip() 
                    
                    # Extract Status Text
                    status_match = re.search(r'>([^<]+)</div>', status_chunk)
                    if not status_match:
                        status_match = re.search(r'text-black">([^<]+)</div>', status_chunk)
                    if not status_match:
                        continue
                    
                    status_text = status_match.group(1).strip()
                    
                    # Ultra-Robust Format Detection
                    combined = f"{slug} {title} {current_series_name}".lower()
                    fmt_hint = 'other'
                    if 't20' in combined or 'hundred' in combined:
                        fmt_hint = 't20'
                    elif 'odi' in combined or 'one day' in combined:
                        fmt_hint = 'odi'
                    elif 'test' in combined or 'stumps' in combined or 'day ' in combined:
                        fmt_hint = 'test'
                    elif 't10' in combined:
                        fmt_hint = 't10'

                    # Clean title extraction: "5th T20I • Christchurch, Hagley Oval"
                    # But if title is empty, use slug
                    clean_title = title if title else slug.replace('-', ' ')

                    # Extract teams from slug
                    parts = slug.split('-')
                    team1_hint = parts[0].upper() if parts else 'Unknown'
                    team2_hint = parts[2].upper() if len(parts) > 2 else 'Unknown'

                    rows.append(NormalizedMatch(
                        source='cricbuzz_web',
                        source_id=cb_id,
                        name=clean_title,
                        series_name=current_series_name,
                        team1_name=team1_hint,
                        team2_name=team2_hint,
                        format=normalize_format(fmt_hint),
                        status=normalize_status(status_text),
                        result_text=status_text,
                        category=infer_category(series_name=current_series_name, match_name=clean_title),
                        raw_data={'slug': slug, 'scraped_title': title, 'scraped_series': current_series_name},
                        sources=['cricbuzz', 'web_scrape']
                    ))
                
        logger.info(f"Cricbuzz Web Scrape successfully retrieved {len(rows)} match statuses")
        return rows
    except Exception as e:
        logger.warning(f"Cricbuzz Web Scrape error: {e}")
        return []


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def sync_player_stats(self, match_id: str | None = None):
    """Sync player-level scorecard stats for one match or recent completed matches."""
    from apps.matches.models import Match, MatchScorecard, Team
    from apps.players.models import Player, PlayerMatchStats

    try:
        logger.info("Starting sync_player_stats task")
        targets = []
        targets = []
        if match_id:
            targets = [str(match_id)]
        else:
            # Prioritize live matches for deep sync (scorecards/mini), then recently completed ones.
            # We target matches that have either CricAPI or Cricbuzz IDs.
            q_live = Match.objects.filter(status='live').exclude(cricapi_id='', cricbuzz_id='')
            q_complete = Match.objects.filter(status='complete').exclude(cricapi_id='', cricbuzz_id='')
            
            # Use CricAPI ID if available, otherwise fallback to Cricbuzz ID
            live_targets = []
            for m in q_live[:15]:
                live_targets.append(m.cricapi_id or m.cricbuzz_id)
            
            complete_targets = []
            for m in q_complete[:10]:
                complete_targets.append(m.cricapi_id or m.cricbuzz_id)
                
            targets = live_targets + complete_targets

        synced = 0
        failed = 0
        for source_match_id in targets:
            try:
                # 1. Core API Lookup
                payload = {}
                try:
                    payload = _cricapi_get('/match_scorecard', {'id': source_match_id}, health_key='match_scoreboard')
                except Exception as cric_err:
                    logger.debug(f"CricAPI match_scorecard failed for {source_match_id}: {cric_err}")

                rows = _iter_scorecard_rows(payload)
                scoreboard_payload = payload # Keep reference
                
                if not rows:
                    # 2. Fallback to RapidAPI Standard
                    scoreboard_payload = _rapidapi_get_with_fallback(
                        [RAPIDAPI_ENDPOINTS['match_scoreboard'].format(match_id=source_match_id)],
                        health_key='match_scoreboard',
                    )
                    rows = _iter_scorecard_rows(scoreboard_payload)
                
                if not rows:
                    # 3. Fallback to RapidAPI MCenter (Super Accurate)
                    scoreboard_payload = _rapidapi_get_with_fallback(
                        [RAPIDAPI_ENDPOINTS['mcenter']['scorecard_v2'].format(match_id=source_match_id)],
                        health_key='mcenter_scoreboard',
                        provider_force='rapidapi_cricbuzz2'
                    )
                    rows = _iter_scorecard_rows(scoreboard_payload)
                
                # PRELUDE: Match Object Retrieval
                match_obj = Match.objects.filter(models.Q(cricapi_id=source_match_id) | models.Q(cricbuzz_id=source_match_id)).first()
                if not match_obj and source_match_id.isdigit():
                    match_obj = Match.objects.filter(id=int(source_match_id)).first()
                
                if not match_obj:
                    continue

                if not rows:
                    # 4. FINAL FALLBACK: Cricbuzz Web Scraper (Deep Scrape)
                    # Inspired by the unofficial scrapers found in sanwebinfo and mskian projects.
                    logger.info(f"sync_player_stats: All APIs failed for {source_match_id}. Trying Deep Web Scrape...")
                    scraped_data = _scrape_cricbuzz_scorecard(source_match_id)
                    if scraped_data and scraped_data.get('scorecards'):
                        _process_scraped_scorecard(match_obj, scraped_data)
                        synced += 1
                        continue
                    else:
                        continue

                # Extract 'Super Live' Data from miniscore (if available)
                mini = scoreboard_payload.get('miniscore') or scoreboard_payload.get('miniscoreRecord') or {}
                match_obj.live_status_text = str(mini.get('status') or mini.get('customStatus') or match_obj.result_text)[:500]
                match_obj.last_balls = str(mini.get('recentOvers') or mini.get('lastBallCommentary') or '')[:200]
                
                # Proactive status inference: if status text says "won by", mark as complete
                inferred_status = normalize_status(match_obj.live_status_text)
                if inferred_status == 'complete' and match_obj.status == 'live':
                    match_obj.status = 'complete'
                    match_obj.result_text = match_obj.live_status_text
                
                # Current Batters
                curr_bats = []
                bat_list = mini.get('batsman') or mini.get('batters') or []
                for b in bat_list:
                    curr_bats.append({
                        'name': b.get('name') or b.get('batsmanName') or 'Unknown',
                        'runs': b.get('runs') or b.get('r') or 0,
                        'balls': b.get('balls') or b.get('b') or 0,
                        'on_strike': b.get('onStrike') == '1' or b.get('strike') == True
                    })
                match_obj.current_batters = curr_bats

                # Current Bowlers
                curr_bowls = []
                bowl_list = mini.get('bowler') or mini.get('bowlers') or []
                for bw in bowl_list:
                    curr_bowls.append({
                        'name': bw.get('name') or bw.get('bowlerName') or 'Unknown',
                        'overs': bw.get('overs') or bw.get('o') or 0,
                        'runs': bw.get('runs') or bw.get('r') or 0,
                        'wickets': bw.get('wickets') or bw.get('w') or 0
                    })
                match_obj.current_bowlers = curr_bowls
                match_obj.save()

                for innings_index, innings in enumerate(rows, start=1):
                    innings_num = innings.get('inningsNumber') or innings.get('inningsId') or innings.get('inningsid') or innings_index
                    batting_team_name = innings.get('batTeamName') or innings.get('batteamname') or innings.get('battingTeam') or ''
                    batting_team = None
                    if batting_team_name:
                        batting_team, _ = Team.objects.get_or_create(name=batting_team_name)

                    MatchScorecard.objects.update_or_create(
                        match=match_obj,
                        innings_number=int(innings_num),
                        defaults={
                            'batting_team': batting_team,
                            'total_runs': int(innings.get('score') or (innings.get('total') or {}).get('runs') or innings.get('runs') or 0),
                            'total_wickets': int(innings.get('wickets') or (innings.get('total') or {}).get('wickets') or 0),
                            'total_overs': float(innings.get('overs') or (innings.get('total') or {}).get('overs') or 0),
                            'run_rate': float(innings.get('runRate') or innings.get('runrate') or 0),
                            'crr': float(innings.get('crr') or mini.get('crr') or 0),
                            'rrr': float(innings.get('rrr') or mini.get('rrr') or 0),
                            'batting_data': innings.get('batting') or innings.get('batters') or innings.get('bat') or innings.get('batsman') or innings.get('batsmenData') or [],
                            'bowling_data': innings.get('bowling') or innings.get('bowlers') or innings.get('bowl') or innings.get('bowler') or innings.get('bowlersData') or [],
                        },
                    )

                    bat_raw = innings.get('batting') or innings.get('batters') or innings.get('bat') or innings.get('batsman') or innings.get('batsmenData') or []
                    for batter in bat_raw:
                        batter_name = batter.get('batsmanName') or batter.get('name') or batter.get('title')
                        if not batter_name:
                            continue
                        
                        player, _ = Player.objects.get_or_create(name=batter_name, defaults={'team': batting_team})
                        PlayerMatchStats.objects.update_or_create(
                            player=player,
                            match=match_obj,
                            innings_number=int(innings_num),
                            defaults={
                                'runs_scored': int(batter.get('runs') or batter.get('r') or 0),
                                'balls_faced': int(batter.get('balls') or batter.get('b') or 0),
                                'fours': int(batter.get('fours') or batter.get('f4') or batter.get('4s') or 0),
                                'sixes': int(batter.get('sixes') or batter.get('s6') or batter.get('6s') or 0),
                                'strike_rate': float(batter.get('strikeRate') or batter.get('sr') or batter.get('strkrate') or 0),
                                'dismissed': str(batter.get('outdec') or batter.get('outDesc') or batter.get('status') or '').strip().lower() not in ('not out', 'yet to bat', ''),
                            },
                        )

                    bowl_raw = innings.get('bowling') or innings.get('bowlers') or innings.get('bowl') or innings.get('bowler') or innings.get('bowlersData') or []
                    for bowler in bowl_raw:
                        bowler_name = bowler.get('bowlerName') or bowler.get('name') or bowler.get('title')
                        if not bowler_name:
                            continue
                        player, _ = Player.objects.get_or_create(name=bowler_name)
                        PlayerMatchStats.objects.update_or_create(
                            player=player,
                            match=match_obj,
                            innings_number=int(innings_num),
                            defaults={
                                'overs_bowled': float(bowler.get('overs') or bowler.get('o') or 0),
                                'runs_conceded': int(bowler.get('runs') or bowler.get('r') or 0),
                                'wickets_taken': int(bowler.get('wickets') or bowler.get('w') or 0),
                                'economy': float(bowler.get('economy') or bowler.get('eco') or 0),
                                'maidens': int(bowler.get('maidens') or bowler.get('m') or 0),
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
def run_rolling_window_retraining_pipeline(years: int | None = None):
    """Train and persist model using the most recent N years of completed matches."""
    from apps.matches.models import Match

    window_years = max(1, int(years or getattr(settings, 'ML_ROLLING_WINDOW_YEARS', 3)))
    latest_year = Match.objects.filter(
        status='complete',
        match_date__isnull=False,
    ).aggregate(max_year=models.Max('match_date__year')).get('max_year')

    if not latest_year:
        payload = {
            'status': 'skipped',
            'reason': 'no complete matches with match_date found',
            'window_years': window_years,
        }
        cache.set('pipeline:model_retraining:rolling:last_result', payload, 24 * 60 * 60)
        cache.set('pipeline:model_retraining:rolling:last_run_at', timezone.now().isoformat(), 24 * 60 * 60)
        return payload

    end_year = int(latest_year)
    start_year = int(end_year - window_years + 1)
    version = f"{settings.ML_MODEL_VERSION}-rolling-{start_year}-{end_year}"

    summary = train_models_for_year_range(
        settings.ML_MODEL_PATH,
        version=version,
        start_year=start_year,
        end_year=end_year,
    )
    payload = {
        'status': 'complete',
        'version': summary.version,
        'sample_count': summary.sample_count,
        'model_type': summary.model_type,
        'accuracy': summary.accuracy,
        'auc_roc': summary.auc_roc,
        'brier_score': summary.brier_score,
        'start_year': start_year,
        'end_year': end_year,
        'window_years': window_years,
    }
    cache.set('pipeline:model_retraining:rolling:last_result', payload, 24 * 60 * 60)
    cache.set('pipeline:model_retraining:rolling:last_run_at', timezone.now().isoformat(), 24 * 60 * 60)
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
            payload, provider, _ = _rapidapi_get_with_fallback(
                [path],
                health_key=f'teams_{category}',
                return_meta=True,
            )
            rows = _team_rows_from_payload(payload)

            for row in rows:
                name = str(row.get('teamName') or row.get('name') or row.get('title') or '').strip()
                if not name:
                    continue

                dedupe_key = name.lower()
                if dedupe_key in seen_names:
                    continue

                seen_names.add(dedupe_key)
                team_obj, _ = Team.objects.update_or_create(
                    name=name,
                    defaults={
                        'short_name': str(row.get('shortName') or row.get('short_name') or '')[:10],
                        'country': str(row.get('country') or row.get('nation') or ''),
                        'logo_url': _row_logo_value(row),
                        'is_international': category in {'international', 'women'},
                        'primary_source': (provider or 'rapidapi_free'),
                        'confidence_score': 75,
                        'source_urls': [
                            {
                                'provider': (provider or 'rapidapi_free'),
                                'timestamp': timezone.now().isoformat(),
                            }
                        ],
                    },
                )

                update_team_source(
                    team_obj,
                    field_name='name',
                    value=name,
                    provider=(provider or 'rapidapi_free'),
                    confidence_score=80,
                )
                if team_obj.short_name:
                    update_team_source(
                        team_obj,
                        field_name='short_name',
                        value=team_obj.short_name,
                        provider=(provider or 'rapidapi_free'),
                        confidence_score=72,
                    )
                if team_obj.country:
                    update_team_source(
                        team_obj,
                        field_name='country',
                        value=team_obj.country,
                        provider=(provider or 'rapidapi_free'),
                        confidence_score=75,
                    )
                if team_obj.logo_url:
                    update_team_source(
                        team_obj,
                        field_name='logo_url',
                        value=team_obj.logo_url,
                        provider=(provider or 'rapidapi_free'),
                        confidence_score=65,
                    )
                team_obj.save()
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
            # RapidAPI team IDs are provider-scoped and do not necessarily match local DB IDs.
            team_ids = list(range(1, 26))

        synced = 0
        failed = 0
        for source_team_id in team_ids:
            try:
                path = RAPIDAPI_ENDPOINTS['players_by_team'].format(team_id=source_team_id)
                payload, provider, _ = _rapidapi_get_with_fallback(
                    [path],
                    health_key='players_by_team',
                    return_meta=True,
                )
                rows = _player_rows_from_payload(payload)
                if not rows:
                    continue

                team_obj = Team.objects.filter(id=source_team_id).first()
                for row in rows:
                    player_id = str(row.get('id') or row.get('playerId') or row.get('pid') or '')
                    player_name = str(row.get('name') or row.get('playerName') or row.get('title') or '').strip()
                    if not player_name:
                        continue

                    defaults = {
                        'full_name': str(row.get('fullName') or row.get('full_name') or row.get('title') or player_name),
                        'country': str(row.get('country') or row.get('nationality') or ''),
                        'role': _normalize_player_role(str(row.get('role') or row.get('playerRole') or '')),
                        'batting_style': str(row.get('battingStyle') or row.get('batting_style') or ''),
                        'bowling_style': str(row.get('bowlingStyle') or row.get('bowling_style') or ''),
                        'image_url': str(row.get('image') or row.get('imageUrl') or row.get('playerImg') or ''),
                        'team': team_obj,
                        'raw_data': row,
                        'primary_source': (provider or 'rapidapi_free'),
                        'confidence_score': 72,
                        'source_urls': [
                            {
                                'provider': (provider or 'rapidapi_free'),
                                'timestamp': timezone.now().isoformat(),
                            }
                        ],
                    }

                    if player_id:
                        player_obj, _ = Player.objects.update_or_create(
                            cricapi_id=player_id,
                            defaults={'name': player_name, **defaults},
                        )
                    else:
                        player_obj, _ = Player.objects.update_or_create(name=player_name, defaults=defaults)

                    update_player_source(
                        player_obj,
                        field_name='name',
                        value=player_name,
                        provider=(provider or 'rapidapi_free'),
                        confidence_score=78,
                    )
                    if player_obj.country:
                        update_player_source(
                            player_obj,
                            field_name='country',
                            value=player_obj.country,
                            provider=(provider or 'rapidapi_free'),
                            confidence_score=70,
                        )
                    if player_obj.role:
                        update_player_source(
                            player_obj,
                            field_name='role',
                            value=player_obj.role,
                            provider=(provider or 'rapidapi_free'),
                            confidence_score=68,
                        )
                    if player_obj.image_url:
                        update_player_source(
                            player_obj,
                            field_name='image_url',
                            value=player_obj.image_url,
                            provider=(provider or 'rapidapi_free'),
                            confidence_score=64,
                        )
                    player_obj.save()
                    synced += 1
            except Exception:
                failed += 1
                continue

        if synced == 0:
            # Fallback catalog when team-scoped fetches return empty payloads.
            payload, provider, _ = _rapidapi_get_with_fallback(
                [LEGACY_RAPIDAPI_ENDPOINTS['players_trending']],
                health_key='players_trending',
                return_meta=True,
            )
            rows = _player_rows_from_payload(payload)
            for row in rows:
                player_id = str(row.get('id') or row.get('playerId') or row.get('pid') or '')
                player_name = str(row.get('name') or row.get('playerName') or row.get('title') or '').strip()
                if not player_name:
                    continue
                defaults = {
                    'full_name': str(row.get('fullName') or row.get('full_name') or row.get('title') or player_name),
                    'country': str(row.get('country') or row.get('nationality') or ''),
                    'role': _normalize_player_role(str(row.get('role') or row.get('playerRole') or '')),
                    'batting_style': str(row.get('battingStyle') or row.get('batting_style') or ''),
                    'bowling_style': str(row.get('bowlingStyle') or row.get('bowling_style') or ''),
                    'image_url': str(row.get('image') or row.get('imageUrl') or row.get('playerImg') or ''),
                    'raw_data': row,
                }
                if player_id:
                    player_obj, _ = Player.objects.update_or_create(
                        cricapi_id=player_id,
                        defaults={'name': player_name, **defaults},
                    )
                else:
                    player_obj, _ = Player.objects.update_or_create(name=player_name, defaults=defaults)

                update_player_source(
                    player_obj,
                    field_name='name',
                    value=player_name,
                    provider=(provider or 'cricbuzz2'),
                    confidence_score=76,
                )
                if player_obj.country:
                    update_player_source(
                        player_obj,
                        field_name='country',
                        value=player_obj.country,
                        provider=(provider or 'cricbuzz2'),
                        confidence_score=70,
                    )
                if player_obj.role:
                    update_player_source(
                        player_obj,
                        field_name='role',
                        value=player_obj.role,
                        provider=(provider or 'cricbuzz2'),
                        confidence_score=72,
                    )
                player_obj.save()
                synced += 1

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
    
    cricapi_rows = []
    try:
        cricapi_rows = [normalize_cricapi_match(row) for row in _cricapi_get('/currentMatches').get('data', [])]
    except Exception as e:
        logger.warning(f"sync_unified_matches: CricAPI fetch failed: {e}")

    cricbuzz_rows = []
    cricbuzz_provider = 'cricbuzz2'
    try:
        cricbuzz_rows, cricbuzz_provider, _ = _extract_live_rows_with_fallback([
            RAPIDAPI_ENDPOINTS['live_scores'],
            RAPIDAPI_ENDPOINTS['matches']['live'],
            LEGACY_RAPIDAPI_ENDPOINTS['live_scores'],
            LIVESCORE6_ENDPOINTS['live_scores'],
        ])
    except Exception as e:
        logger.warning(f"sync_unified_matches: RapidAPI fetch failed: {e}")
    
    # NEW: Ultra-Accuracy Fallback from Cricbuzz Web Scraper
    scraped_rows = []
    try:
        scraped_rows = _scrape_cricbuzz_livescores()
    except Exception as e:
        logger.warning(f"sync_unified_matches: Web scraper failed: {e}")
    
    merged = merge_and_dedupe_matches(cricapi_rows + cricbuzz_rows + scraped_rows)

    synced = 0
    for row in merged:
        provider = 'cricapi' if row.source == 'cricapi' else (cricbuzz_provider or 'cricbuzz2')
        _upsert_match(row, source_provider=provider)
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


def _scrape_cricbuzz_scorecard(cricbuzz_id: str):
    """
    Directly scrapes the scorecard page for deep-syncing when APIs lag.
    Inspired by open-source scrapers found in sanwebinfo/cricket-api.
    """
    url = f"https://www.cricbuzz.com/live-cricket-scorecard/{cricbuzz_id}/"
    logger.info(f"Deep Scraping Scorecard: {url}")
    
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                return None
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'lxml')
            
            # Identify Innings
            # Cricbuzz uses id="innings_1", id="innings_2" etc for the containers
            scorecard_data = []
            for i in range(1, 3):
                innings_div = soup.find('div', id=f'innings_{i}')
                if not innings_div: continue
                
                # Get Team Name and Total
                header = innings_div.find('div', class_='cb-col cb-col-100 cb-ltnd-stts')
                if not header: continue
                
                # Header text usually: "New Zealand Innings 162-5 (20 Ovs)"
                h_text = header.get_text()
                team_name = h_text.split('Innings')[0].strip()
                
                # Extract Score: 162-5
                score_match = re.search(r'(\d+)(?:-(\d+))?', h_text)
                runs = int(score_match.group(1)) if score_match else 0
                wickets = int(score_match.group(2)) if score_match and score_match.group(2) else 10 # If all out, wickets might not show as -X
                
                # Extract Overs
                overs_match = re.search(r'\((\d+\.?\d*)\s*Ovs\)', h_text)
                overs = float(overs_match.group(1)) if overs_match else 0.0
                
                # Basic Innings Record
                innings_record = {
                    'innings_number': i,
                    'batting_team_name': team_name,
                    'total_runs': runs,
                    'total_wickets': wickets,
                    'total_overs': overs,
                    'is_current': True if i == 2 or (i == 1 and not soup.find('div', id='innings_2')) else False
                }
                scorecard_data.append(innings_record)
                
            return {
                'scorecards': scorecard_data,
                'source': 'cricbuzz_deep_scrape'
            }
    except Exception as exc:
        logger.error(f"_scrape_cricbuzz_scorecard error: {exc}")
        return None


def _process_scraped_scorecard(match_obj, scraped_data):
    """Integrates scraped innings data into MatchScorecard records."""
    from apps.matches.models import MatchScorecard, Team
    
    for item in scraped_data.get('scorecards', []):
        innings_num = item.get('innings_number')
        team_name = item.get('batting_team_name')
        
        team_obj = None
        if team_name:
            team_obj, _ = Team.objects.get_or_create(name=team_name)
            
        MatchScorecard.objects.update_or_create(
            match=match_obj,
            innings_number=innings_num,
            defaults={
                'batting_team': team_obj,
                'total_runs': item.get('total_runs', 0),
                'total_wickets': item.get('total_wickets', 0),
                'total_overs': item.get('total_overs', 0.0),
                'crr': 0, # Scraper would need more regex for this
                'rrr': 0,
                'batting_data': [], # Scraper would need deep individual row parsing
                'bowling_data': [],
            }
        )
    
    # Update match status if it's currently live and scraper shows comprehensive data
    if match_obj.status == 'live' and len(scraped_data.get('scorecards', [])) > 0:
        match_obj.save() # Just refresh timestamp


@shared_task(bind=True)
def sync_from_github_data(self, json_url: str):
    """
    Experimental: Pull cricket data from a raw GitHub JSON feed.
    Schema varies, this handles common 'unofficial API' patterns.
    """
    logger.info(f"Starting sync_from_github_data from {json_url}")
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(json_url)
            resp.raise_for_status()
            data = resp.json()
            
            # Common patterns: { matches: [...] } or just [...]
            results = data.get('matches') if isinstance(data, dict) else data
            if not isinstance(results, list):
                logger.warning("GitHub data was not a list of matches")
                return {'synced': 0}
            
            from .normalizers import NormalizedMatch, normalize_status, normalize_format
            rows = []
            for item in results:
                # Map fields (Generic mapping for common unofficial schemas)
                name = item.get('name') or item.get('match_name') or 'Match'
                status_raw = item.get('status') or item.get('live_status') or 'upcoming'
                
                rows.append(NormalizedMatch(
                    source='github_free',
                    source_id=str(item.get('id') or item.get('match_id') or ''),
                    name=name,
                    team1_name=item.get('team1') or 'Team 1',
                    team2_name=item.get('team2') or 'Team 2',
                    status=normalize_status(status_raw),
                    format=normalize_format(item.get('format') or item.get('match_type')),
                    result_text=item.get('result') or item.get('status_text') or '',
                    raw_data=item,
                    sources=['github_public']
                ))
            
            synced = 0
            for row in rows:
                _upsert_match(row, source_provider='github_public')
                synced += 1
                
            return {'synced': synced}
    except Exception as exc:
        logger.error(f"GitHub data sync failed: {exc}")
        return {'synced': 0}
