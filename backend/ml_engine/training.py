"""Model training entrypoints for Phase 3 pre-match prediction."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, date

from django.db.models import Q

from apps.matches.models import Match
from .loader import save_bundle

logger = logging.getLogger(__name__)

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

FORMAT_MAP = {'test': 0.25, 'odi': 0.5, 't20': 0.75, 't10': 1.0, 'other': 0.6}
PITCH_MAP = {'batting': 1.0, 'balanced': 0.5, 'bowling': 0.0}


@dataclass
class TrainingSummary:
    version: str
    sample_count: int
    model_type: str
    accuracy: float | None = None
    auc_roc: float | None = None
    brier_score: float | None = None


def _safe_rate(wins: int, total: int, default: float = 0.5) -> float:
    return float(wins / total) if total else default


def _features_for_match(target_match: Match) -> dict[str, float]:
    features: dict[str, float] = {}

    for i, team in enumerate([target_match.team1, target_match.team2], 1):
        if not team:
            features[f'team{i}_win_rate_last10'] = 0.5
            features[f'team{i}_matches_last10'] = 0.0
            continue

        prior_matches = Match.objects.filter(
            Q(team1=team) | Q(team2=team),
            status='complete',
            format=target_match.format,
            match_date__lt=target_match.match_date,
        ).order_by('-match_date')[:10]
        total = prior_matches.count()
        team_pk = int(getattr(team, 'pk', 0) or 0)
        wins = sum(1 for row in prior_matches if int(getattr(row, 'winner_id', 0) or 0) == team_pk)
        features[f'team{i}_win_rate_last10'] = _safe_rate(wins, total)
        features[f'team{i}_matches_last10'] = float(total)

    h2h_rows = Match.objects.filter(
        Q(team1=target_match.team1, team2=target_match.team2)
        | Q(team1=target_match.team2, team2=target_match.team1),
        status='complete',
        match_date__lt=target_match.match_date,
    ).order_by('-match_date')[:20]

    h2h_total = h2h_rows.count()
    target_team1_pk = int(getattr(target_match, 'team1_id', 0) or 0)
    h2h_t1_wins = sum(1 for row in h2h_rows if int(getattr(row, 'winner_id', 0) or 0) == target_team1_pk)
    features['h2h_team1_win_rate'] = _safe_rate(h2h_t1_wins, h2h_total)
    features['h2h_total_matches'] = float(h2h_total)

    features['format_encoded'] = FORMAT_MAP.get(target_match.format, 0.6)

    pitch_type = target_match.venue.pitch_type if target_match.venue else 'balanced'
    avg_score = target_match.venue.avg_first_innings_score if target_match.venue else None
    features['venue_pitch_type'] = PITCH_MAP.get(pitch_type, 0.5)
    features['venue_avg_score'] = float(avg_score if avg_score is not None else 150.0)

    return features


def _build_dataset() -> tuple[list[list[float]], list[int]]:
    matches = Match.objects.select_related('team1', 'team2', 'venue', 'winner').filter(
        status='complete',
        team1__isnull=False,
        team2__isnull=False,
        winner__isnull=False,
        match_date__isnull=False,
    ).order_by('match_date', 'id')

    X_rows: list[list[float]] = []
    y_rows: list[int] = []

    for match in matches:
        features = _features_for_match(match)
        X_rows.append([features[col] for col in FEATURE_COLUMNS])
        winner_pk = int(getattr(match, 'winner_id', 0) or 0)
        team1_pk = int(getattr(match, 'team1_id', 0) or 0)
        y_rows.append(1 if winner_pk == team1_pk else 0)

    if not X_rows:
        return [], []

    return X_rows, y_rows


def _build_dataset_for_year_range(start_year: int, end_year: int) -> tuple[list[list[float]], list[int]]:
    """Build a dataset constrained to matches in an inclusive year range."""
    if start_year > end_year:
        start_year, end_year = end_year, start_year

    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)

    matches = Match.objects.select_related('team1', 'team2', 'venue', 'winner').filter(
        status='complete',
        team1__isnull=False,
        team2__isnull=False,
        winner__isnull=False,
        match_date__isnull=False,
        match_date__gte=start_date,
        match_date__lte=end_date,
    ).order_by('match_date', 'id')

    X_rows: list[list[float]] = []
    y_rows: list[int] = []

    for match in matches:
        features = _features_for_match(match)
        X_rows.append([features[col] for col in FEATURE_COLUMNS])
        winner_pk = int(getattr(match, 'winner_id', 0) or 0)
        team1_pk = int(getattr(match, 'team1_id', 0) or 0)
        y_rows.append(1 if winner_pk == team1_pk else 0)

    if not X_rows:
        return [], []

    return X_rows, y_rows


def train_models_from_matches(model_path: str, version: str = 'v1.1') -> TrainingSummary:
    """Train and persist a pre-match model bundle from completed matches."""
    X, y = _build_dataset()
    if len(X) < 20:
        logger.warning('Insufficient training samples for robust model training')
        summary = TrainingSummary(version=version, sample_count=int(len(X)), model_type='fallback')
        save_bundle(
            model_path,
            version,
            {
                'type': 'fallback',
                'feature_columns': FEATURE_COLUMNS,
                'bias': 0.5,
                'trained_at': datetime.utcnow().isoformat(),
            },
            {
                'sample_count': int(len(X)),
                'model_type': 'fallback',
                'note': 'Need at least 20 labeled completed matches for sklearn training.',
            },
        )
        return summary

    try:
        import importlib

        sklearn_ensemble = importlib.import_module('sklearn.ensemble')
        sklearn_metrics = importlib.import_module('sklearn.metrics')
        sklearn_model_selection = importlib.import_module('sklearn.model_selection')

        RandomForestClassifier = sklearn_ensemble.RandomForestClassifier
        GradientBoostingClassifier = sklearn_ensemble.GradientBoostingClassifier
        accuracy_score = sklearn_metrics.accuracy_score
        roc_auc_score = sklearn_metrics.roc_auc_score
        brier_score_loss = sklearn_metrics.brier_score_loss
        train_test_split = sklearn_model_selection.train_test_split
    except Exception as exc:  # pragma: no cover - import guard for minimal envs
        logger.warning(f'scikit-learn unavailable; saving fallback model bundle: {exc}')
        summary = TrainingSummary(version=version, sample_count=int(len(X)), model_type='fallback')
        save_bundle(
            model_path,
            version,
            {
                'type': 'fallback',
                'feature_columns': FEATURE_COLUMNS,
                'bias': float(sum(y) / len(y)) if len(y) else 0.5,
                'trained_at': datetime.utcnow().isoformat(),
            },
            {
                'sample_count': int(len(X)),
                'model_type': 'fallback',
                'note': 'scikit-learn missing in runtime environment',
            },
        )
        return summary

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    rf = RandomForestClassifier(n_estimators=250, random_state=42)
    gb = GradientBoostingClassifier(random_state=42)
    rf.fit(X_train, y_train)
    gb.fit(X_train, y_train)

    rf_prob = rf.predict_proba(X_test)[:, 1]
    gb_prob = gb.predict_proba(X_test)[:, 1]
    ensemble_prob = (0.6 * rf_prob) + (0.4 * gb_prob)
    y_pred = (ensemble_prob >= 0.5).astype(int)

    accuracy = float(accuracy_score(y_test, y_pred))
    auc = float(roc_auc_score(y_test, ensemble_prob))
    brier = float(brier_score_loss(y_test, ensemble_prob))

    bundle = {
        'type': 'sklearn_ensemble',
        'feature_columns': FEATURE_COLUMNS,
        'rf': rf,
        'gb': gb,
        'weights': {'rf': 0.6, 'gb': 0.4},
        'trained_at': datetime.utcnow().isoformat(),
    }
    save_bundle(
        model_path,
        version,
        bundle,
        {
            'sample_count': int(len(X)),
            'model_type': 'sklearn_ensemble',
            'accuracy': round(accuracy, 4),
            'auc_roc': round(auc, 4),
            'brier_score': round(brier, 4),
        },
    )

    return TrainingSummary(
        version=version,
        sample_count=int(len(X)),
        model_type='sklearn_ensemble',
        accuracy=round(accuracy, 4),
        auc_roc=round(auc, 4),
        brier_score=round(brier, 4),
    )


def train_models_for_year_range(
    model_path: str,
    version: str,
    start_year: int,
    end_year: int,
) -> TrainingSummary:
    """Train and persist a model using matches from a specific inclusive year range."""
    X, y = _build_dataset_for_year_range(start_year=start_year, end_year=end_year)
    if len(X) < 20:
        logger.warning('Insufficient year-range samples for robust training')
        summary = TrainingSummary(version=version, sample_count=int(len(X)), model_type='fallback')
        save_bundle(
            model_path,
            version,
            {
                'type': 'fallback',
                'feature_columns': FEATURE_COLUMNS,
                'bias': 0.5,
                'trained_at': datetime.utcnow().isoformat(),
                'year_range': {'start_year': int(start_year), 'end_year': int(end_year)},
            },
            {
                'sample_count': int(len(X)),
                'model_type': 'fallback',
                'note': 'Need at least 20 labeled completed matches for sklearn training.',
                'year_range': {'start_year': int(start_year), 'end_year': int(end_year)},
            },
        )
        return summary

    try:
        import importlib

        sklearn_ensemble = importlib.import_module('sklearn.ensemble')
        sklearn_metrics = importlib.import_module('sklearn.metrics')
        sklearn_model_selection = importlib.import_module('sklearn.model_selection')

        RandomForestClassifier = sklearn_ensemble.RandomForestClassifier
        GradientBoostingClassifier = sklearn_ensemble.GradientBoostingClassifier
        accuracy_score = sklearn_metrics.accuracy_score
        roc_auc_score = sklearn_metrics.roc_auc_score
        brier_score_loss = sklearn_metrics.brier_score_loss
        train_test_split = sklearn_model_selection.train_test_split
    except Exception as exc:  # pragma: no cover - import guard for minimal envs
        logger.warning(f'scikit-learn unavailable; saving fallback model bundle: {exc}')
        summary = TrainingSummary(version=version, sample_count=int(len(X)), model_type='fallback')
        save_bundle(
            model_path,
            version,
            {
                'type': 'fallback',
                'feature_columns': FEATURE_COLUMNS,
                'bias': float(sum(y) / len(y)) if len(y) else 0.5,
                'trained_at': datetime.utcnow().isoformat(),
                'year_range': {'start_year': int(start_year), 'end_year': int(end_year)},
            },
            {
                'sample_count': int(len(X)),
                'model_type': 'fallback',
                'note': 'scikit-learn missing in runtime environment',
                'year_range': {'start_year': int(start_year), 'end_year': int(end_year)},
            },
        )
        return summary

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    rf = RandomForestClassifier(n_estimators=250, random_state=42)
    gb = GradientBoostingClassifier(random_state=42)
    rf.fit(X_train, y_train)
    gb.fit(X_train, y_train)

    rf_prob = rf.predict_proba(X_test)[:, 1]
    gb_prob = gb.predict_proba(X_test)[:, 1]
    ensemble_prob = (0.6 * rf_prob) + (0.4 * gb_prob)
    y_pred = (ensemble_prob >= 0.5).astype(int)

    accuracy = float(accuracy_score(y_test, y_pred))
    auc = float(roc_auc_score(y_test, ensemble_prob))
    brier = float(brier_score_loss(y_test, ensemble_prob))

    bundle = {
        'type': 'sklearn_ensemble',
        'feature_columns': FEATURE_COLUMNS,
        'rf': rf,
        'gb': gb,
        'weights': {'rf': 0.6, 'gb': 0.4},
        'trained_at': datetime.utcnow().isoformat(),
        'year_range': {'start_year': int(start_year), 'end_year': int(end_year)},
    }
    save_bundle(
        model_path,
        version,
        bundle,
        {
            'sample_count': int(len(X)),
            'model_type': 'sklearn_ensemble',
            'accuracy': round(accuracy, 4),
            'auc_roc': round(auc, 4),
            'brier_score': round(brier, 4),
            'year_range': {'start_year': int(start_year), 'end_year': int(end_year)},
        },
    )

    return TrainingSummary(
        version=version,
        sample_count=int(len(X)),
        model_type='sklearn_ensemble',
        accuracy=round(accuracy, 4),
        auc_roc=round(auc, 4),
        brier_score=round(brier, 4),
    )
