"""Prediction helpers for Phase 3 model inference."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from django.db.models import Q

from apps.matches.models import Match
from .loader import load_bundle
from .training import FEATURE_COLUMNS


FORMAT_MAP = {'test': 0.25, 'odi': 0.5, 't20': 0.75, 't10': 1.0, 'other': 0.6}
PITCH_MAP = {'batting': 1.0, 'balanced': 0.5, 'bowling': 0.0}


def _safe_rate(wins: int, total: int, default: float = 0.5) -> float:
	return float(wins / total) if total else default


def build_pre_match_features(match_id: int) -> dict[str, float]:
	match = Match.objects.select_related('team1', 'team2', 'venue').get(pk=match_id)
	features: dict[str, float] = {}

	for i, team in enumerate([match.team1, match.team2], 1):
		if not team:
			features[f'team{i}_win_rate_last10'] = 0.5
			features[f'team{i}_matches_last10'] = 0.0
			continue

		last_10 = Match.objects.filter(
			Q(team1=team) | Q(team2=team),
			status='complete',
			format=match.format,
		).order_by('-match_date')[:10]
		wins = sum(1 for row in last_10 if row.winner_id == team.id)
		total = last_10.count()
		features[f'team{i}_win_rate_last10'] = _safe_rate(wins, total)
		features[f'team{i}_matches_last10'] = float(total)

	h2h_rows = Match.objects.filter(
		Q(team1=match.team1, team2=match.team2)
		| Q(team1=match.team2, team2=match.team1),
		status='complete',
	).order_by('-match_date')[:20]
	h2h_total = h2h_rows.count()
	h2h_team1_wins = sum(1 for row in h2h_rows if row.winner_id == match.team1_id)

	features['h2h_team1_win_rate'] = _safe_rate(h2h_team1_wins, h2h_total)
	features['h2h_total_matches'] = float(h2h_total)
	features['format_encoded'] = FORMAT_MAP.get(match.format, 0.6)

	pitch = match.venue.pitch_type if match.venue else 'balanced'
	avg_score = match.venue.avg_first_innings_score if match.venue else None
	features['venue_pitch_type'] = PITCH_MAP.get(pitch, 0.5)
	features['venue_avg_score'] = float(avg_score if avg_score is not None else 150.0)

	return features


def _features_to_array(features: dict[str, float]) -> list[list[float]]:
	return [[float(features.get(col, 0.0)) for col in FEATURE_COLUMNS]]


@lru_cache(maxsize=8)
def _cached_bundle(model_path: str, model_version: str) -> dict[str, Any] | None:
	return load_bundle(model_path, model_version)


def _fallback_probability(features: dict[str, float], bias: float = 0.5) -> float:
	score = (
		0.45 * features.get('team1_win_rate_last10', 0.5)
		+ 0.25 * features.get('h2h_team1_win_rate', 0.5)
		+ 0.10 * features.get('format_encoded', 0.6)
		+ 0.05 * features.get('venue_pitch_type', 0.5)
		+ 0.15 * bias
	)
	return float(min(max(score, 0.05), 0.95))


def predict_match(match_id: int, model_path: str, model_version: str) -> dict[str, Any]:
	features = build_pre_match_features(match_id)
	X = _features_to_array(features)
	bundle = _cached_bundle(model_path, model_version)

	if not bundle:
		team1_prob = _fallback_probability(features)
		model_kind = 'fallback_untrained'
	elif bundle.get('type') == 'sklearn_ensemble':
		rf = bundle['rf']
		gb = bundle['gb']
		weights = bundle.get('weights', {'rf': 0.6, 'gb': 0.4})
		rf_prob = float(rf.predict_proba(X)[0][1])
		gb_prob = float(gb.predict_proba(X)[0][1])
		team1_prob = (weights['rf'] * rf_prob) + (weights['gb'] * gb_prob)
		team1_prob = float(min(max(team1_prob, 0.05), 0.95))
		model_kind = 'sklearn_ensemble'
	else:
		team1_prob = _fallback_probability(features, float(bundle.get('bias', 0.5)))
		model_kind = bundle.get('type', 'fallback')

	team2_prob = float(1.0 - team1_prob)
	confidence = float(min(abs(team1_prob - 0.5) * 2 + 0.35, 1.0))

	key_factors = [
		{
			'factor': 'recent_form_delta',
			'impact': round(abs(features.get('team1_win_rate_last10', 0.5) - features.get('team2_win_rate_last10', 0.5)), 4),
			'direction': 'team1' if features.get('team1_win_rate_last10', 0.5) > features.get('team2_win_rate_last10', 0.5) else 'team2',
		},
		{
			'factor': 'head_to_head',
			'impact': round(abs(features.get('h2h_team1_win_rate', 0.5) - 0.5), 4),
			'direction': 'team1' if features.get('h2h_team1_win_rate', 0.5) > 0.5 else 'team2',
		},
	]

	return {
		'team1_win_probability': round(team1_prob, 4),
		'team2_win_probability': round(team2_prob, 4),
		'draw_probability': 0.0,
		'confidence_score': round(confidence, 4),
		'key_factors': key_factors,
		'feature_snapshot': features,
		'model_version': model_version,
		'model_kind': model_kind,
	}
