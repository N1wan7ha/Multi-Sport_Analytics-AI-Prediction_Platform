"""Prediction tasks used by Phase 2 API endpoints."""
from celery import shared_task
from django.conf import settings
from django.utils import timezone

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


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def process_prediction_job(self, job_id: int):
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
                    'model_kind': prediction['model_kind'],
                    'features': prediction['feature_snapshot'],
                },
            },
        )
        job.model_version = prediction['model_version']
        job.status = 'complete'
        job.completed_at = timezone.now()
        job.error_message = ''
        job.save(update_fields=['status', 'completed_at', 'error_message', 'model_version'])
        return {'status': 'complete', 'job_id': job.pk, 'result_id': result.pk}
    except Exception as exc:
        job.status = 'failed'
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'error_message', 'completed_at'])
        raise self.retry(exc=exc)
