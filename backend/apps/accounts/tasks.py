from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.matches.models import Match, Team
from apps.predictions.models import PredictionJob

from .models import NotificationDispatch, UserFavouriteTeam


def _render_match_start_subject(match: Match) -> str:
    return f"Match starting soon: {match.name}"


def _render_match_start_body(match: Match) -> str:
    start_time = match.match_datetime.isoformat() if match.match_datetime else 'scheduled soon'
    return (
        f"Your favourite team has a match starting soon.\n\n"
        f"Match: {match.name}\n"
        f"Start time: {start_time}\n"
        f"Format: {match.format.upper()}\n"
        f"Category: {match.category}\n"
    )


def _render_prediction_ready_subject(job: PredictionJob) -> str:
    return f"Prediction ready for {job.match.name}"


def _render_prediction_ready_body(job: PredictionJob) -> str:
    result = getattr(job, 'result', None)
    if not result:
        return f"Your prediction job #{job.pk} for {job.match.name} is complete."

    return (
        f"Your prediction job is complete.\n\n"
        f"Match: {job.match.name}\n"
        f"{result.team1.name}: {result.team1_win_probability:.2%}\n"
        f"{result.team2.name}: {result.team2_win_probability:.2%}\n"
        f"Confidence: {result.confidence_score:.2f}\n"
    )


@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def send_match_start_notifications(self):
    window_minutes = int(getattr(settings, 'MATCH_START_NOTIFICATION_WINDOW_MINUTES', 30))
    now = timezone.now()
    upper = now + timedelta(minutes=window_minutes)

    upcoming = Match.objects.filter(
        status='upcoming',
        match_datetime__isnull=False,
        match_datetime__gte=now,
        match_datetime__lte=upper,
    ).select_related('team1', 'team2')

    sent_count = 0
    for match in upcoming:
        team_ids = [tid for tid in [getattr(match, 'team1_id', None), getattr(match, 'team2_id', None)] if tid]
        if not team_ids:
            continue

        users = UserFavouriteTeam.objects.filter(team_id__in=team_ids).select_related('user')
        for favourite in users:
            user = favourite.user
            if not user.email or not user.is_active:
                continue

            already_sent = NotificationDispatch.objects.filter(
                user=user,
                notification_type='match_start',
                match=match,
            ).exists()
            if already_sent:
                continue

            send_mail(
                subject=_render_match_start_subject(match),
                message=_render_match_start_body(match),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@matchmind.dev'),
                recipient_list=[user.email],
                fail_silently=True,
            )
            NotificationDispatch.objects.create(
                user=user,
                notification_type='match_start',
                match=match,
            )
            sent_count += 1

    return {'sent': sent_count, 'window_minutes': window_minutes}


@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def send_prediction_ready_notifications(self):
    jobs = PredictionJob.objects.filter(
        status='complete',
        requested_by__isnull=False,
    ).select_related('requested_by', 'match', 'result__team1', 'result__team2')

    sent_count = 0
    for job in jobs:
        user = job.requested_by
        if not user or not user.email or not user.is_active:
            continue

        already_sent = NotificationDispatch.objects.filter(
            user=user,
            notification_type='prediction_ready',
            prediction_job=job,
        ).exists()
        if already_sent:
            continue

        send_mail(
            subject=_render_prediction_ready_subject(job),
            message=_render_prediction_ready_body(job),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@matchmind.dev'),
            recipient_list=[user.email],
            fail_silently=True,
        )
        NotificationDispatch.objects.create(
            user=user,
            notification_type='prediction_ready',
            prediction_job=job,
        )
        sent_count += 1

    return {'sent': sent_count}
