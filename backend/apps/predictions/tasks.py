"""Prediction tasks used by Phase 2 API endpoints."""
import re
from typing import Any
from importlib import import_module

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from asgiref.sync import async_to_sync

from apps.matches.models import Match
from config.celery import app as celery_app
from ml_engine.predictor import predict_match

from .models import PredictionJob, PredictionResult


def _compute_prediction(job: PredictionJob):
    """Run model inference for the current prediction job."""
    match_pk = int(getattr(job.match, 'pk', 0) or 0)
    return predict_match(
        match_id=match_pk,
        model_path=settings.ML_MODEL_PATH,
        model_version=job.model_version,
    )


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

    prediction['confidence_score'] = round(confidence, 4)
    prediction['key_factors'] = key_factors
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
