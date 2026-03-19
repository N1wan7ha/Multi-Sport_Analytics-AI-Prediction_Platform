"""Normalization and deduplication utilities for cricket data feeds."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

FRANCHISE_KEYWORDS = [
    'ipl', 'bbl', 'cpl', 'psl', 'bpl', 'lpl', 'hundred', 'sa20', 'mlc',
    'ilt20', 't10', 'super smash', 'big bash', 'caribbean premier', 'pakistan super',
]

STATUS_ORDER = {
    'live': 3,
    'complete': 2,
    'upcoming': 1,
    'abandoned': 0,
}


@dataclass
class NormalizedMatch:
    source: str
    source_id: str
    name: str
    series_name: str = ''
    team1_name: str = 'Unknown'
    team2_name: str = 'Unknown'
    format: str = 'other'
    status: str = 'upcoming'
    category: str = 'international'
    match_date: str = ''
    venue_name: str = ''
    result_text: str = ''
    raw_data: dict[str, Any] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.sources:
            self.sources = [self.source]


def normalize_format(value: str | None) -> str:
    fmt = str(value or '').strip().lower()
    if fmt == 'test':
        return 'test'
    if fmt == 'odi':
        return 'odi'
    if fmt in ('t20', 't20i'):
        return 't20'
    if fmt == 't10':
        return 't10'
    return 'other'


def normalize_status(value: str | None) -> str:
    text = str(value or '').strip().lower()
    if not text:
        return 'upcoming'
    if any(word in text for word in ('scheduled', 'preview', 'fixture')):
        return 'upcoming'
    if any(word in text for word in ('live', 'inning', 'day ', 'stumps')):
        return 'live'
    if any(word in text for word in ('won', 'draw', 'abandoned', 'no result', 'tie', 'result')):
        return 'complete'
    return 'upcoming'


def infer_category(series_name: str = '', match_name: str = '', hint: str = '') -> str:
    lowered_hint = str(hint or '').lower()
    if 'international' in lowered_hint:
        return 'international'
    if 'league' in lowered_hint:
        return 'franchise'

    combined = f"{series_name} {match_name}".lower()
    if any(keyword in combined for keyword in FRANCHISE_KEYWORDS):
        return 'franchise'
    return 'international'


def normalize_name(name: str | None) -> str:
    return ' '.join(str(name or '').strip().lower().split())


def team_key(name: str | None) -> str:
    return normalize_name(name)


def parse_date(raw_value: Any) -> str:
    if raw_value is None:
        return ''

    text = str(raw_value).strip()
    if not text:
        return ''

    if text.isdigit():
        try:
            ms_value = int(text)
            return datetime.fromtimestamp(ms_value / 1000, tz=timezone.utc).date().isoformat()
        except (ValueError, OSError):
            return ''

    if len(text) >= 10:
        return text[:10]

    return ''


def split_teams_from_name(name: str) -> tuple[str, str]:
    if ' vs ' in name:
        left, right = name.split(' vs ', 1)
        return left.strip(), right.split(',')[0].strip()
    return 'Unknown', 'Unknown'


def normalize_cricapi_match(row: dict[str, Any]) -> NormalizedMatch:
    match_name = row.get('name', '')
    teams = row.get('teams') or []

    team1, team2 = ('Unknown', 'Unknown')
    if isinstance(teams, list) and len(teams) >= 2:
        team1, team2 = str(teams[0]), str(teams[1])
    else:
        team1, team2 = split_teams_from_name(match_name)

    return NormalizedMatch(
        source='cricapi',
        source_id=str(row.get('id', '')),
        name=match_name,
        series_name=row.get('series') or row.get('seriesName', ''),
        team1_name=team1,
        team2_name=team2,
        format=normalize_format(row.get('matchType', '')),
        status=normalize_status(row.get('status', '')),
        category=infer_category(row.get('series') or row.get('seriesName', ''), match_name),
        match_date=parse_date(row.get('date') or row.get('dateTimeGMT')),
        venue_name=row.get('venue', ''),
        result_text=row.get('status', ''),
        raw_data=row,
    )


def normalize_cricbuzz_live_match(match_info: dict[str, Any], category_hint: str = '', series_name: str = '') -> NormalizedMatch:
    team1 = str((match_info.get('team1') or {}).get('teamName', 'Unknown'))
    team2 = str((match_info.get('team2') or {}).get('teamName', 'Unknown'))
    match_name = f"{team1} vs {team2}"

    return NormalizedMatch(
        source='cricbuzz',
        source_id=str(match_info.get('matchId', '')),
        name=match_name,
        series_name=series_name,
        team1_name=team1,
        team2_name=team2,
        format=normalize_format(match_info.get('matchFormat', '')),
        status='live',
        category=infer_category(series_name=series_name, match_name=match_name, hint=category_hint),
        match_date=parse_date(match_info.get('startDate')),
        venue_name=(match_info.get('venueInfo') or {}).get('ground', ''),
        result_text='',
        raw_data=match_info,
    )


def normalize_cricbuzz_recent_match(match_info: dict[str, Any], category_hint: str = '', series_name: str = '') -> NormalizedMatch:
    team1 = str((match_info.get('team1') or {}).get('teamName', 'Unknown'))
    team2 = str((match_info.get('team2') or {}).get('teamName', 'Unknown'))
    match_name = f"{team1} vs {team2}"

    return NormalizedMatch(
        source='cricbuzz',
        source_id=str(match_info.get('matchId', '')),
        name=match_name,
        series_name=series_name,
        team1_name=team1,
        team2_name=team2,
        format=normalize_format(match_info.get('matchFormat', '')),
        status='complete',
        category=infer_category(series_name=series_name, match_name=match_name, hint=category_hint),
        match_date=parse_date(match_info.get('startDate')),
        venue_name=(match_info.get('venueInfo') or {}).get('ground', ''),
        result_text=str(match_info.get('status', '')),
        raw_data=match_info,
    )


def fingerprint(match: NormalizedMatch) -> str:
    teams = sorted([team_key(match.team1_name), team_key(match.team2_name)])
    date = match.match_date[:10] if match.match_date else ''
    return f"{'|'.join(teams)}__{date}__{match.format}"


def _similar_pair(a: NormalizedMatch, b: NormalizedMatch) -> bool:
    if a.format != b.format:
        return False
    if a.match_date and b.match_date and a.match_date[:10] != b.match_date[:10]:
        return False

    a_teams = sorted([team_key(a.team1_name), team_key(a.team2_name)])
    b_teams = sorted([team_key(b.team1_name), team_key(b.team2_name)])
    ratio = SequenceMatcher(None, '|'.join(a_teams), '|'.join(b_teams)).ratio()
    return ratio >= 0.93


def merge_matches(left: NormalizedMatch, right: NormalizedMatch) -> NormalizedMatch:
    merged = NormalizedMatch(
        source=f"{left.source}+{right.source}",
        source_id=left.source_id or right.source_id,
        name=left.name or right.name,
        series_name=left.series_name or right.series_name,
        team1_name=left.team1_name or right.team1_name,
        team2_name=left.team2_name or right.team2_name,
        format=left.format or right.format,
        status=left.status,
        category=left.category or right.category,
        match_date=left.match_date or right.match_date,
        venue_name=left.venue_name or right.venue_name,
        result_text=left.result_text or right.result_text,
        raw_data={**left.raw_data, **right.raw_data},
        sources=sorted(set(left.sources + right.sources)),
    )

    if STATUS_ORDER.get(right.status, 0) > STATUS_ORDER.get(merged.status, 0):
        merged.status = right.status

    if not merged.category:
        merged.category = infer_category(merged.series_name, merged.name)
    return merged


def merge_and_dedupe_matches(matches: list[NormalizedMatch]) -> list[NormalizedMatch]:
    deduped: dict[str, NormalizedMatch] = {}
    fallback: list[NormalizedMatch] = []

    for match in matches:
        if not match.team1_name and not match.team2_name:
            fallback.append(match)
            continue

        key = fingerprint(match)
        existing = deduped.get(key)
        if existing:
            deduped[key] = merge_matches(existing, match)
        else:
            deduped[key] = match

    for candidate in fallback:
        merged_existing = False
        for key, existing in list(deduped.items()):
            if _similar_pair(existing, candidate):
                deduped[key] = merge_matches(existing, candidate)
                merged_existing = True
                break
        if not merged_existing:
            deduped[fingerprint(candidate)] = candidate

    return list(deduped.values())
