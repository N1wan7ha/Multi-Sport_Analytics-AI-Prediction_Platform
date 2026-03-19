"""Data pipeline Celery tasks — syncs cricket data from APIs to PostgreSQL."""
import logging
from celery import shared_task
from django.conf import settings
import httpx

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


# ─────────────────────────────────────────────────
# Normalization (ported from normalize.js + merge.js)
# ─────────────────────────────────────────────────

FRANCHISE_KEYWORDS = [
    'ipl', 'bbl', 'cpl', 'psl', 'bpl', 'lpl', 'hundred', 'sa20', 'mlc',
    'ilt20', 't10', 'super smash', 'big bash', 'caribbean premier', 'pakistan super'
]


def normalize_format(fmt: str) -> str:
    v = str(fmt or '').lower()
    if v in ('test',): return 'test'
    if v in ('odi',): return 'odi'
    if v in ('t20', 't20i'): return 't20'
    if v in ('t10',): return 't10'
    return 'other'


def infer_category(series_name: str = '', match_name: str = '', hint: str = '') -> str:
    hint = hint.lower()
    if 'international' in hint: return 'international'
    if 'league' in hint: return 'franchise'
    combined = f"{series_name} {match_name}".lower()
    for kw in FRANCHISE_KEYWORDS:
        if kw in combined:
            return 'franchise'
    return 'international'


def normalize_cricapi_status(status_text: str) -> str:
    t = status_text.lower() if status_text else ''
    if not t: return 'upcoming'
    if any(w in t for w in ['scheduled', 'preview']): return 'upcoming'
    if any(w in t for w in ['live', 'inning', 'day ', 'stumps']): return 'live'
    if any(w in t for w in ['won', 'draw', 'abandoned', 'no result', 'tie']): return 'complete'
    return 'upcoming'


# ─────────────────────────────────────────────────
# Celery Tasks
# ─────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_current_matches(self):
    """Pull active/current matches from CricAPI → save to DB."""
    from apps.matches.models import Match, Team
    try:
        logger.info("Starting sync_current_matches task")
        data = _cricapi_get('/currentMatches')
        rows = data.get('data', [])
        synced = 0

        for row in rows:
            match_id = str(row.get('id', ''))
            if not match_id:
                continue

            # Get or create teams
            teams_raw = row.get('teams', [])
            team1_obj = team2_obj = None
            if len(teams_raw) >= 2:
                team1_obj, _ = Team.objects.get_or_create(name=teams_raw[0])
                team2_obj, _ = Team.objects.get_or_create(name=teams_raw[1])

            Match.objects.update_or_create(
                cricapi_id=match_id,
                defaults={
                    'name': row.get('name', ''),
                    'format': normalize_format(row.get('matchType', '')),
                    'status': normalize_cricapi_status(row.get('status', '')),
                    'team1': team1_obj,
                    'team2': team2_obj,
                    'raw_data': row,
                }
            )
            synced += 1

        logger.info(f"sync_current_matches: synced {synced} matches")
        return {'synced': synced}

    except Exception as exc:
        logger.error(f"sync_current_matches failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def sync_cricbuzz_live(self):
    """Pull live matches from Cricbuzz RapidAPI → update DB."""
    from apps.matches.models import Match, Team
    try:
        logger.info("Starting sync_cricbuzz_live task")
        data = _cricbuzz_get('/matches/v1/live')
        type_matches = data.get('typeMatches', [])
        synced = 0

        for type_match in type_matches:
            category_hint = type_match.get('matchType', '').lower()
            for series_match in type_match.get('seriesMatches', []):
                wrapper = series_match.get('seriesAdWrapper', {})
                matches = series_match.get('matches', wrapper.get('matches', []))
                series_name = wrapper.get('seriesName', '')

                for match in matches:
                    info = match.get('matchInfo', {})
                    if not info:
                        continue

                    cricbuzz_id = str(info.get('matchId', ''))
                    team1_name = info.get('team1', {}).get('teamName', 'Unknown')
                    team2_name = info.get('team2', {}).get('teamName', 'Unknown')

                    team1_obj, _ = Team.objects.get_or_create(name=team1_name)
                    team2_obj, _ = Team.objects.get_or_create(name=team2_name)

                    import datetime
                    start_ms = info.get('startDate')
                    match_date = None
                    if start_ms:
                        try:
                            match_date = datetime.datetime.fromtimestamp(
                                int(start_ms) / 1000
                            ).date()
                        except Exception:
                            pass

                    Match.objects.update_or_create(
                        cricbuzz_id=cricbuzz_id,
                        defaults={
                            'name': f"{team1_name} vs {team2_name}",
                            'format': normalize_format(info.get('matchFormat', '')),
                            'category': infer_category(series_name, hint=category_hint),
                            'status': 'live',
                            'team1': team1_obj,
                            'team2': team2_obj,
                            'match_date': match_date,
                            'raw_data': info,
                        }
                    )
                    synced += 1

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
                    'raw_data': row,
                }
            )
            synced += 1
        logger.info(f"sync_series: synced {synced} series")
        return {'synced': synced}
    except Exception as exc:
        logger.error(f"sync_series failed: {exc}")
        raise self.retry(exc=exc)
