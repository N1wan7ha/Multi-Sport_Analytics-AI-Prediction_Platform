"""Prediction tasks used by Phase 2 API endpoints."""
from collections import defaultdict
import re
from statistics import mean
from typing import Any
from importlib import import_module

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from asgiref.sync import async_to_sync

from apps.core.gender import infer_match_gender_bucket
from apps.matches.models import Match, MatchScorecard
from apps.players.models import PlayerMatchStats
from config.celery import app as celery_app
from ml_engine.predictor import predict_match

from .models import PredictionJob, PredictionResult


FORMAT_DEFAULT_TOTALS = {
    'test': {'runs': 340.0, 'wickets': 6.0},
    'odi': {'runs': 276.0, 'wickets': 7.2},
    't20': {'runs': 168.0, 'wickets': 6.5},
    't10': {'runs': 112.0, 'wickets': 6.0},
    'other': {'runs': 180.0, 'wickets': 6.8},
}


def _compute_prediction(job: PredictionJob):
    """Run model inference for the current prediction job."""
    match_pk = int(getattr(job.match, 'pk', 0) or 0)
    requested_version = job.model_version
    if bool(getattr(settings, 'ML_AUTO_SELECT_BEST_MODEL', True)):
        requested_version = 'auto'
    return predict_match(
        match_id=match_pk,
        model_path=settings.ML_MODEL_PATH,
        model_version=requested_version,
    )


def _estimate_team_totals(team, match_format: str, gender_bucket: str = 'men') -> dict[str, Any]:
    defaults = FORMAT_DEFAULT_TOTALS.get(match_format, FORMAT_DEFAULT_TOTALS['other'])
    if not team:
        base_runs = int(round(defaults['runs']))
        spread = int(max(8, round(base_runs * 0.09)))
        return {
            'team_id': None,
            'team_name': 'Unknown',
            'projected_score': base_runs,
            'projected_score_range': [max(40, base_runs - spread), min(450, base_runs + spread)],
            'projected_wickets_lost': round(float(defaults['wickets']), 1),
            'sample_size': 0,
        }

    innings_rows = list(
        MatchScorecard.objects.filter(
            match__status='complete',
            match__format=match_format,
            batting_team=team,
        )
        .select_related('match__team1', 'match__team2')
        .exclude(total_runs__isnull=True)
        .order_by('-match__match_date', '-id')[:80]
    )
    innings_rows = [row for row in innings_rows if infer_match_gender_bucket(row.match) == gender_bucket][:24]

    if innings_rows:
        avg_runs = mean(float(row.total_runs or 0) for row in innings_rows)
        avg_wickets = mean(float(row.total_wickets or 0) for row in innings_rows)
        sample_size = len(innings_rows)
    else:
        avg_runs = float(defaults['runs'])
        avg_wickets = float(defaults['wickets'])
        sample_size = 0

    projected_score = int(round(max(40.0, min(avg_runs, 450.0))))
    projected_wickets = round(max(1.5, min(avg_wickets, 10.0)), 1)
    spread = int(max(8, round(projected_score * 0.09)))
    return {
        'team_id': int(team.id),
        'team_name': team.name,
        'projected_score': projected_score,
        'projected_score_range': [max(40, projected_score - spread), min(450, projected_score + spread)],
        'projected_wickets_lost': projected_wickets,
        'sample_size': sample_size,
    }


def _player_form_candidates(team, match_format: str, gender_bucket: str = 'men') -> list[dict[str, Any]]:
    if not team:
        return []

    rows = list(
        PlayerMatchStats.objects.filter(
            player__team=team,
            match__status='complete',
            match__format=match_format,
            match__match_date__isnull=False,
        )
        .select_related('player', 'match__team1', 'match__team2')
        .order_by('-match__match_date', '-id')[:600]
    )
    rows = [row for row in rows if infer_match_gender_bucket(row.match) == gender_bucket][:300]

    if not rows:
        return []

    by_player: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            'player': None,
            'innings': 0,
            'runs': 0.0,
            'wickets': 0.0,
            'strike_rate_total': 0.0,
            'strike_rate_count': 0,
            'economy_total': 0.0,
            'economy_count': 0,
            'boundaries': 0.0,
            'maidens': 0.0,
        }
    )

    for row in rows:
        if not row.player_id:
            continue
        data = by_player[int(row.player_id)]
        data['player'] = row.player
        data['innings'] += 1
        data['runs'] += float(row.runs_scored or 0)
        data['wickets'] += float(row.wickets_taken or 0)
        data['boundaries'] += float((row.fours or 0) + (row.sixes or 0))
        data['maidens'] += float(row.maidens or 0)

        if row.strike_rate is not None:
            data['strike_rate_total'] += float(row.strike_rate)
            data['strike_rate_count'] += 1
        if row.economy is not None:
            data['economy_total'] += float(row.economy)
            data['economy_count'] += 1

    candidates: list[dict[str, Any]] = []
    for player_id, data in by_player.items():
        innings = int(data['innings'])
        if innings <= 0:
            continue

        avg_runs = float(data['runs']) / float(innings)
        avg_wickets = float(data['wickets']) / float(innings)
        avg_strike_rate = (
            float(data['strike_rate_total']) / float(data['strike_rate_count'])
            if int(data['strike_rate_count']) > 0
            else 0.0
        )
        avg_economy = (
            float(data['economy_total']) / float(data['economy_count'])
            if int(data['economy_count']) > 0
            else 7.5
        )
        boundary_rate = float(data['boundaries']) / float(innings)

        batting_index = (avg_runs * 0.72) + (avg_strike_rate * 0.09) + (boundary_rate * 0.22)
        bowling_index = (avg_wickets * 4.0) - (avg_economy * 0.35) + ((float(data['maidens']) / float(innings)) * 0.45)
        all_rounder_index = (avg_runs * 0.45) + (avg_wickets * 4.9) - (avg_economy * 0.22)

        player = data.get('player')
        candidates.append(
            {
                'player_id': player_id,
                'player_name': getattr(player, 'name', 'Unknown'),
                'team_id': int(team.id),
                'team_name': team.name,
                'sample_size': innings,
                'batting_index': float(batting_index),
                'bowling_index': float(bowling_index),
                'all_rounder_index': float(all_rounder_index),
            }
        )

    return candidates


def _pick_top_performer(candidates: list[dict[str, Any]], metric_key: str) -> dict[str, Any] | None:
    if not candidates:
        return None

    best = max(
        candidates,
        key=lambda row: (float(row.get(metric_key, 0.0)), int(row.get('sample_size', 0))),
    )
    return {
        'player_id': int(best['player_id']),
        'player_name': str(best['player_name']),
        'team_id': int(best['team_id']),
        'team_name': str(best['team_name']),
        'form_index': round(float(best.get(metric_key, 0.0)), 3),
        'sample_size': int(best.get('sample_size', 0)),
    }


def _build_pre_match_projection(job: PredictionJob, prediction: dict[str, Any]) -> dict[str, Any]:
    gender_bucket = infer_match_gender_bucket(job.match)
    team1_projection = _estimate_team_totals(job.match.team1, job.match.format, gender_bucket=gender_bucket)
    team2_projection = _estimate_team_totals(job.match.team2, job.match.format, gender_bucket=gender_bucket)

    team1_candidates = _player_form_candidates(job.match.team1, job.match.format, gender_bucket=gender_bucket)
    team2_candidates = _player_form_candidates(job.match.team2, job.match.format, gender_bucket=gender_bucket)
    combined_candidates = [*team1_candidates, *team2_candidates]

    projected_winner = team1_projection
    team1_prob = float(prediction.get('team1_win_probability', 0.5))
    team2_prob = float(prediction.get('team2_win_probability', 0.5))
    winner_probability = team1_prob
    if team2_prob > team1_prob:
        projected_winner = team2_projection
        winner_probability = team2_prob

    model_features = prediction.get('feature_snapshot') or {}
    insights: list[str] = []
    h2h_rate = model_features.get('h2h_team1_win_rate')
    if h2h_rate is not None and job.match.team1 and job.match.team2:
        favored = job.match.team1.name if float(h2h_rate) >= 0.5 else job.match.team2.name
        insights.append(f"Head-to-head edge slightly favors {favored}.")

    venue = getattr(job.match, 'venue', None)
    venue_avg = getattr(venue, 'avg_first_innings_score', None)
    if venue_avg is not None:
        insights.append(f"Venue first-innings baseline is around {int(round(float(venue_avg)))} runs.")

    score_gap = abs(int(team1_projection['projected_score']) - int(team2_projection['projected_score']))
    if score_gap >= 20:
        insights.append('Projected scoring gap is significant based on recent form and format profile.')

    projection = {
        'gender_segment': gender_bucket,
        'projected_winner': {
            'team_id': projected_winner.get('team_id'),
            'team_name': projected_winner.get('team_name', ''),
            'win_probability': round(float(winner_probability), 4),
        },
        'team_totals': {
            'team1': team1_projection,
            'team2': team2_projection,
        },
        'top_performers': {
            'top_batter': _pick_top_performer(combined_candidates, 'batting_index'),
            'best_bowler': _pick_top_performer(combined_candidates, 'bowling_index'),
            'best_all_rounder': _pick_top_performer(combined_candidates, 'all_rounder_index'),
        },
        'insights': insights,
    }

    prediction['pre_match_projection'] = projection
    key_factors = list(prediction.get('key_factors') or [])
    key_factors.append(
        {
            'factor': 'projected_total_gap',
            'impact': round(float(score_gap) / 100.0, 4),
            'direction': 'team1' if int(team1_projection['projected_score']) >= int(team2_projection['projected_score']) else 'team2',
        }
    )
    prediction['key_factors'] = key_factors
    return prediction


def _max_overs_for_format(match_format: str) -> int:
    mapping = {
        'odi': 50,
        't20': 20,
        't10': 10,
        'test': 90,
    }
    return mapping.get(match_format, 50)


def _parse_score(score: str) -> tuple[int | None, int | None]:
    if not score:
        return None, None
    match = re.match(r'^(\d+)(?:\/(\d+))?$', score.strip())
    if not match:
        return None, None
    runs = int(match.group(1))
    wickets = int(match.group(2)) if match.group(2) is not None else None
    return runs, wickets


def _apply_live_context(job: PredictionJob, prediction: dict, current_over: int | None, current_score: str) -> dict:
    """Apply in-match context to confidence and explanatory factors."""
    if current_over is None:
        return prediction

    max_overs = _max_overs_for_format(job.match.format)
    progress = min(max(float(current_over) / float(max_overs), 0.0), 1.0)
    confidence = float(prediction['confidence_score'])
    confidence = min(1.0, confidence + (0.25 * progress))

    runs, wickets = _parse_score(current_score)
    pressure = None
    if runs is not None and current_over > 0:
        run_rate = runs / max(current_over, 1)
        if job.match.format == 't20':
            par = 8.0
        elif job.match.format == 'odi':
            par = 5.0
        elif job.match.format == 't10':
            par = 9.0
        else:
            par = 3.5
        wickets_penalty = (wickets or 0) * 0.25
        pressure = round(run_rate - par - wickets_penalty, 3)

    key_factors = list(prediction.get('key_factors') or [])
    key_factors.append(
        {
            'factor': 'live_progress',
            'impact': round(progress, 4),
            'direction': 'neutral',
        }
    )
    if pressure is not None:
        key_factors.append(
            {
                'factor': 'innings_pressure_index',
                'impact': abs(pressure),
                'direction': 'positive' if pressure >= 0 else 'negative',
            }
        )

    features = prediction.get('feature_snapshot') or {}
    team_strength = float(features.get('team1_win_rate_last10', 0.5)) - float(features.get('team2_win_rate_last10', 0.5))
    team_strength_score = round(min(max((team_strength + 1.0) / 2.0, 0.0), 1.0), 4)

    last_balls = str(getattr(job.match, 'last_balls', '') or '').strip()
    momentum_raw = 0.0
    for token in last_balls.split():
        t = token.strip().lower()
        if t in {'w', 'wk', 'out'}:
            momentum_raw -= 1.5
        elif t in {'0', '.'}:
            momentum_raw -= 0.1
        elif t == '1':
            momentum_raw += 0.2
        elif t == '2':
            momentum_raw += 0.35
        elif t == '3':
            momentum_raw += 0.45
        elif t == '4':
            momentum_raw += 0.8
        elif t == '6':
            momentum_raw += 1.2
        elif t in {'wd', 'nb'}:
            momentum_raw += 0.3
    momentum_score = round(min(max((momentum_raw + 6.0) / 12.0, 0.0), 1.0), 4)

    player_impact_raw = 0.0
    has_live_player_payload = False
    for batter in list(getattr(job.match, 'current_batters', []) or []):
        if not isinstance(batter, dict):
            continue
        has_live_player_payload = True
        runs_b = float(batter.get('runs') or 0)
        balls_b = float(batter.get('balls') or 0)
        strike_rate = (runs_b * 100.0 / balls_b) if balls_b > 0 else 0.0
        player_impact_raw += (runs_b * 0.015) + (strike_rate * 0.002)

    for bowler in list(getattr(job.match, 'current_bowlers', []) or []):
        if not isinstance(bowler, dict):
            continue
        has_live_player_payload = True
        wickets_b = float(bowler.get('wickets') or 0)
        runs_conceded_b = float(bowler.get('runs') or 0)
        player_impact_raw += (wickets_b * 0.35) - (runs_conceded_b * 0.003)

    # Fallback: derive player impact from recent historical player performance if live player feeds are unavailable.
    if not has_live_player_payload:
        gender_bucket = infer_match_gender_bucket(job.match)
        team1 = job.match.team1
        team2 = job.match.team2
        if team1 and team2:
            team1_stats = list(PlayerMatchStats.objects.filter(
                player__team=team1,
                match__status='complete',
                match__match_date__isnull=False,
            ).select_related('match__team1', 'match__team2').order_by('-match__match_date', '-id')[:120])
            team2_stats = list(PlayerMatchStats.objects.filter(
                player__team=team2,
                match__status='complete',
                match__match_date__isnull=False,
            ).select_related('match__team1', 'match__team2').order_by('-match__match_date', '-id')[:120])

            team1_stats = [row for row in team1_stats if infer_match_gender_bucket(row.match) == gender_bucket][:60]
            team2_stats = [row for row in team2_stats if infer_match_gender_bucket(row.match) == gender_bucket][:60]

            def _aggregate(stats_rows) -> float:
                total = 0.0
                count = 0
                for row in stats_rows:
                    runs = float(row.runs_scored or 0)
                    strike_rate = float(row.strike_rate or 0)
                    wickets = float(row.wickets_taken or 0)
                    economy = float(row.economy or 0)
                    total += (runs * 0.01) + (strike_rate * 0.0015) + (wickets * 0.22) - (economy * 0.01)
                    count += 1
                return (total / count) if count else 0.0

            team1_impact = _aggregate(team1_stats)
            team2_impact = _aggregate(team2_stats)
            player_impact_raw = team1_impact - team2_impact

    player_impact_score = round(min(max((player_impact_raw + 2.0) / 8.0, 0.0), 1.0), 4)

    explainability = {
        'team_strength_score': team_strength_score,
        'player_impact_score': player_impact_score,
        'momentum_score': momentum_score,
        'live_progress_score': round(progress, 4),
        'pressure_score': round(pressure, 4) if pressure is not None else None,
    }

    key_factors.extend(
        [
            {
                'factor': 'team_strength_index',
                'impact': abs(team_strength),
                'direction': 'team1' if team_strength >= 0 else 'team2',
            },
            {
                'factor': 'player_impact_index',
                'impact': player_impact_score,
                'direction': 'neutral',
            },
            {
                'factor': 'momentum_index',
                'impact': momentum_score,
                'direction': 'positive' if momentum_score >= 0.5 else 'negative',
            },
        ]
    )

    prediction['confidence_score'] = round(confidence, 4)
    prediction['key_factors'] = key_factors
    prediction['explainability'] = explainability
    return prediction


def _coerce_over(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        over = int(float(value))
        return over if over >= 0 else None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            over = int(float(text))
            return over if over >= 0 else None
        except ValueError:
            return None
    return None


def _extract_live_over_and_score(raw_data: dict | None) -> tuple[int | None, str]:
    if not isinstance(raw_data, dict):
        return None, ''

    over_candidates = {'over', 'overs', 'currentover', 'current_over', 'curr_over', 'overno', 'over_no'}
    score_candidates = {'score', 'currentscore', 'current_score', 'teamscore', 'team_score'}

    stack: list[Any] = [raw_data]
    over = None
    score = ''

    while stack and (over is None or not score):
        node = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                normalized_key = str(key).replace(' ', '').replace('-', '').lower()
                if over is None and normalized_key in over_candidates:
                    over = _coerce_over(value)
                if not score and normalized_key in score_candidates and value is not None:
                    if isinstance(value, dict):
                        runs = value.get('runs')
                        wickets = value.get('wickets')
                        if runs is not None:
                            score = f"{runs}/{wickets}" if wickets is not None else str(runs)
                    else:
                        score = str(value).strip()

                if isinstance(value, (dict, list)):
                    stack.append(value)

        elif isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list)):
                    stack.append(item)

    return over, score


def _serialize_prediction_job(job: PredictionJob) -> dict[str, Any]:
    result = getattr(job, 'result', None)
    if not result:
        return {
            'id': int(job.pk),
            'match': int(getattr(job, 'match_id', 0) or 0),
            'prediction_type': job.prediction_type,
            'status': job.status,
        }

    return {
        'id': int(job.pk),
        'match': int(getattr(job, 'match_id', 0) or 0),
        'prediction_type': job.prediction_type,
        'status': job.status,
        'model_version': job.model_version,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        'result': {
            'team1': {
                'id': int(result.team1_id) if result.team1_id else None,
                'name': result.team1.name if result.team1 else '',
            },
            'team2': {
                'id': int(result.team2_id) if result.team2_id else None,
                'name': result.team2.name if result.team2 else '',
            },
            'team1_win_probability': float(result.team1_win_probability),
            'team2_win_probability': float(result.team2_win_probability),
            'draw_probability': float(result.draw_probability),
            'confidence_score': float(result.confidence_score),
            'key_factors': result.key_factors,
            'feature_snapshot': result.feature_snapshot,
            'explainability': (result.feature_snapshot or {}).get('explainability', {}),
            'pre_match_projection': (result.feature_snapshot or {}).get('pre_match_projection', {}),
            'current_over': result.current_over,
            'current_score': result.current_score,
        },
    }


def _broadcast_prediction_update(job: PredictionJob) -> None:
    channels_layers = import_module('channels.layers')
    get_channel_layer = getattr(channels_layers, 'get_channel_layer')
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    match_id = int(getattr(job, 'match_id', 0) or 0)
    group_name = f'prediction_match_{match_id}'
    payload = {
        'type': 'prediction.update',
        'data': _serialize_prediction_job(job),
    }
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'prediction_update',
            'payload': payload,
        },
    )


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def schedule_live_predictions(self):
    """Auto-trigger live prediction jobs for active matches every N overs."""
    over_step = max(1, int(getattr(settings, 'LIVE_PREDICTION_OVER_STEP', 2)))
    matches = Match.objects.filter(status='live').select_related('team1', 'team2')

    scheduled = 0
    skipped_no_over = 0
    skipped_over_step = 0
    skipped_inflight = 0

    for match in matches:
        current_over, current_score = _extract_live_over_and_score(getattr(match, 'raw_data', {}))
        if current_over is None:
            skipped_no_over += 1
            continue

        match_pk = int(getattr(match, 'pk', 0) or 0)
        cache_key = f'predictions:live:last_trigger_over:{match_pk}'
        last_trigger_over = cache.get(cache_key)
        if last_trigger_over is not None and (current_over - int(last_trigger_over)) < over_step:
            skipped_over_step += 1
            continue

        inflight_exists = PredictionJob.objects.filter(
            match=match,
            prediction_type='live',
            status__in=('pending', 'processing'),
        ).exists()
        if inflight_exists:
            skipped_inflight += 1
            continue

        job = PredictionJob.objects.create(
            match=match,
            prediction_type='live',
            status='pending',
            requested_by=None,
        )
        job_pk = int(getattr(job, 'pk', 0) or 0)
        task_result = celery_app.send_task('apps.predictions.tasks.process_prediction_job', [job_pk, current_over, current_score])
        job.celery_task_id = str(task_result.id)
        job.save(update_fields=['celery_task_id'])

        cache.set(cache_key, current_over, timeout=12 * 60 * 60)
        scheduled += 1

    return {
        'live_matches': matches.count(),
        'scheduled': scheduled,
        'skipped_no_over': skipped_no_over,
        'skipped_over_step': skipped_over_step,
        'skipped_inflight': skipped_inflight,
        'over_step': over_step,
    }


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def process_prediction_job(self, job_id: int, current_over: int | None = None, current_score: str = ''):
    """Generate and persist a prediction result for a job."""
    try:
        job = PredictionJob.objects.select_related('match__team1', 'match__team2').get(pk=job_id)
    except PredictionJob.DoesNotExist:
        return {'status': 'missing', 'job_id': job_id}

    if job.status in ('complete', 'failed'):
        return {'status': job.status, 'job_id': job_id}

    job.status = 'processing'
    job.save(update_fields=['status'])

    try:
        prediction = _compute_prediction(job)
        if job.prediction_type == 'pre_match':
            prediction = _build_pre_match_projection(job, prediction)
        if job.prediction_type == 'live':
            prediction = _apply_live_context(job, prediction, current_over, current_score)
        result, _ = PredictionResult.objects.update_or_create(
            job=job,
            defaults={
                'team1': job.match.team1,
                'team2': job.match.team2,
                'team1_win_probability': prediction['team1_win_probability'],
                'team2_win_probability': prediction['team2_win_probability'],
                'draw_probability': prediction['draw_probability'],
                'confidence_score': prediction['confidence_score'],
                'key_factors': prediction['key_factors'],
                'feature_snapshot': {
                    'prediction_type': job.prediction_type,
                    'format': job.match.format,
                    'category': job.match.category,
                    'status': job.match.status,
                    'live_context': {
                        'current_over': current_over,
                        'current_score': current_score,
                    },
                    'model_kind': prediction['model_kind'],
                    'features': prediction['feature_snapshot'],
                    'explainability': prediction.get('explainability', {}),
                    'pre_match_projection': prediction.get('pre_match_projection', {}),
                },
                'current_over': current_over if job.prediction_type == 'live' else None,
                'current_score': current_score if job.prediction_type == 'live' else '',
            },
        )
        job.model_version = prediction['model_version']
        job.status = 'complete'
        job.completed_at = timezone.now()
        job.error_message = ''
        job.save(update_fields=['status', 'completed_at', 'error_message', 'model_version'])
        job.refresh_from_db()
        _broadcast_prediction_update(job)
        return {'status': 'complete', 'job_id': job.pk, 'result_id': result.pk}
    except Exception as exc:
        job.status = 'failed'
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'error_message', 'completed_at'])
        raise self.retry(exc=exc)
