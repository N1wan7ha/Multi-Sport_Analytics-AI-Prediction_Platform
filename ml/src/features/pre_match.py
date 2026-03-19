"""
Pre-match feature engineering pipeline.

Builds a feature vector for a match before it starts.
Input: match_id → Output: dict of features ready for ML model.
"""
import numpy as np
import pandas as pd
from django.db.models import Avg, Count, Q


def build_pre_match_features(match_id: int) -> dict:
    """
    Build ML-ready feature vector for a pre-match prediction.

    Features (based on hacks.txt notes):
    - Team win rates (last 10 matches)
    - Head-to-head record
    - Home/away performance
    - Top batsmen average last 5 innings
    - Top bowlers economy last 5
    - Venue batting/bowling friendliness
    - Format encoding
    - ICC rankings (TODO: fetch from API)
    """
    from apps.matches.models import Match
    from apps.players.models import PlayerMatchStats

    match = Match.objects.select_related('team1', 'team2', 'venue').get(id=match_id)

    features = {}

    # ── Team form (last 10 matches) ──────────────────────
    for i, team in enumerate([match.team1, match.team2], 1):
        if not team:
            continue
        last_10 = Match.objects.filter(
            Q(team1=team) | Q(team2=team),
            status='complete',
            format=match.format
        ).order_by('-match_date')[:10]

        wins = sum(1 for m in last_10 if m.winner_id == team.id)
        total = last_10.count()
        features[f'team{i}_win_rate_last10'] = wins / total if total else 0.5
        features[f'team{i}_matches_last10'] = total

    # ── Head-to-head ─────────────────────────────────────
    h2h = Match.objects.filter(
        Q(team1=match.team1, team2=match.team2) | Q(team1=match.team2, team2=match.team1),
        status='complete'
    ).order_by('-match_date')[:20]

    t1_h2h_wins = sum(1 for m in h2h if m.winner_id == match.team1_id) if match.team1 else 0
    t2_h2h_wins = sum(1 for m in h2h if m.winner_id == match.team2_id) if match.team2 else 0
    h2h_total = h2h.count()
    features['h2h_team1_win_rate'] = t1_h2h_wins / h2h_total if h2h_total else 0.5
    features['h2h_total_matches'] = h2h_total

    # ── Format encoding ──────────────────────────────────
    format_map = {'test': 0.25, 'odi': 0.5, 't20': 0.75, 't10': 1.0, 'other': 0.6}
    features['format_encoded'] = format_map.get(match.format, 0.6)

    # ── Venue ────────────────────────────────────────────
    if match.venue:
        pitch_map = {'batting': 1.0, 'balanced': 0.5, 'bowling': 0.0}
        features['venue_pitch_type'] = pitch_map.get(match.venue.pitch_type, 0.5)
        features['venue_avg_score'] = match.venue.avg_first_innings_score or 150.0
    else:
        features['venue_pitch_type'] = 0.5
        features['venue_avg_score'] = 150.0

    return features


def features_to_array(features: dict) -> np.ndarray:
    """Convert feature dict to numpy array in consistent column order."""
    FEATURE_COLUMNS = [
        'team1_win_rate_last10',
        'team2_win_rate_last10',
        'team1_matches_last10',
        'team2_matches_last10',
        'h2h_team1_win_rate',
        'h2h_total_matches',
        'format_encoded',
        'venue_pitch_type',
        'venue_avg_score',
    ]
    return np.array([features.get(col, 0.0) for col in FEATURE_COLUMNS]).reshape(1, -1)
