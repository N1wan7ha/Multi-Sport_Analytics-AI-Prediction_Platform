"""Admin-only API views for platform management."""
from datetime import timedelta
from typing import Any, cast

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminRole
from apps.predictions.models import PredictionJob
from apps.matches.models import Match
from apps.data_pipeline import tasks as pipeline_tasks
from config.celery import app as celery_app
from .serializers import (
    AdminUserSerializer,
    ActivitySummarySerializer,
    PipelineStatusSnapshotSerializer,
    PipelineTaskTriggerSerializer,
    SystemMetricsSerializer,
    AdminPredictionJobSerializer,
    AdminPredictionRetrySerializer,
    AdminPredictionBulkActionSerializer,
)

User = get_user_model()


class AdminPredictionJobsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def _serialize_prediction_job(job: PredictionJob) -> dict:
    return {
        'id': int(getattr(job, 'pk', 0) or 0),
        'match_id': int(getattr(job, 'match_id', 0) or 0),
        'match_name': job.match.name if job.match else '',
        'requested_by_id': int(getattr(job, 'requested_by_id', 0) or 0) or None,
        'requested_by_email': getattr(job.requested_by, 'email', '') if job.requested_by else '',
        'prediction_type': job.prediction_type,
        'status': job.status,
        'model_version': job.model_version,
        'celery_task_id': job.celery_task_id,
        'error_message': job.error_message,
        'requested_at': job.requested_at,
        'completed_at': job.completed_at,
    }


PREDICTION_JOBS_ORDERING_MAP = {
    'requested_at': 'requested_at',
    'status': 'status',
    'type': 'prediction_type',
    'prediction_type': 'prediction_type',
}


def _get_prediction_jobs_ordering(request) -> str:
    raw_ordering = (request.query_params.get('ordering') or '').strip()
    if raw_ordering:
        direction = '-' if raw_ordering.startswith('-') else ''
        key = raw_ordering.lstrip('-')
        mapped_field = PREDICTION_JOBS_ORDERING_MAP.get(key)
        if mapped_field:
            return f'{direction}{mapped_field}'

    sort_by = request.query_params.get('sort_by', 'requested_at')
    sort_dir = (request.query_params.get('sort_dir') or 'desc').lower()
    mapped_field = PREDICTION_JOBS_ORDERING_MAP.get(sort_by, 'requested_at')
    direction = '' if sort_dir == 'asc' else '-'
    return f'{direction}{mapped_field}'


class AdminUserViewSet(viewsets.ModelViewSet):
    """User management for admins: list, retrieve, update, disable."""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = ['role', 'is_active']
    search_fields = ['email', 'username']

    @action(detail=True, methods=['post'])
    def disable_user(self, request, pk=None):
        """Disable a user account (set is_active=False)."""
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'status': 'user disabled'})

    @action(detail=True, methods=['post'])
    def enable_user(self, request, pk=None):
        """Enable a user account (set is_active=True)."""
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'status': 'user enabled'})

    @action(detail=True, methods=['patch'])
    def update_role(self, request, pk=None):
        """Update a user's role (ADMIN or USER)."""
        user = self.get_object()
        new_role = request.data.get('role')
        if new_role not in ['ADMIN', 'USER']:
            return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)
        user.role = new_role
        user.save(update_fields=['role'])
        return Response(AdminUserSerializer(user).data)


class ActivitySummaryView(APIView):
    """Platform activity metrics for admin dashboard."""
    permission_classes = [IsAdminRole]

    def get(self, request):
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        one_day_ago = now - timedelta(days=1)

        # User registrations
        new_registrations_7d = User.objects.filter(date_joined__gte=seven_days_ago).count()
        new_registrations_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()

        # Prediction requests
        prediction_requests_total = PredictionJob.objects.count()
        prediction_requests_pre = PredictionJob.objects.filter(prediction_type='pre_match').count()
        prediction_requests_live = PredictionJob.objects.filter(prediction_type='live').count()

        # Active users (users who requested predictions in last 7 days)
        active_users_7d = PredictionJob.objects.filter(
            requested_at__gte=seven_days_ago
        ).values('requested_by').distinct().count()

        # Data pipeline syncs in last 24 hours (estimated from match updates)
        data_pipeline_syncs_24h = Match.objects.filter(
            updated_at__gte=one_day_ago
        ).values('updated_at').distinct().count()

        data = {
            'new_registrations_7d': new_registrations_7d,
            'new_registrations_30d': new_registrations_30d,
            'prediction_requests_total': prediction_requests_total,
            'pre_match': prediction_requests_pre,
            'live': prediction_requests_live,
            'active_users_7d': active_users_7d,
            'syncs_24h': data_pipeline_syncs_24h,
        }
        serializer = ActivitySummarySerializer(data)
        return Response(serializer.data)


class AdminPipelineStatusView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        payload = {
            'current_matches': cache.get('pipeline:current_matches:last_sync_count')
            or Match.objects.exclude(status='complete').count(),
            'live_matches': cache.get('pipeline:live_matches:last_sync_count')
            or Match.objects.filter(status='live').count(),
            'completed_matches': cache.get('pipeline:completed_matches:last_sync_count')
            or Match.objects.filter(status='complete').count(),
            'player_stats': cache.get('pipeline:player_stats:last_sync_count') or 0,
            'unified_matches': cache.get('pipeline:unified_matches:last_sync_count') or Match.objects.count(),
            'last_model_retraining': cache.get('pipeline:model_retraining:last_run_at') or '',
            'endpoint_health': cache.get('pipeline:endpoint_health:last_success') or {},
        }
        serializer = PipelineStatusSnapshotSerializer(payload)
        return Response(serializer.data)


class AdminPipelineTriggerView(APIView):
    permission_classes = [IsAdminRole]

    task_map = {
        'sync_current_matches': pipeline_tasks.sync_current_matches,
        'sync_cricbuzz_live': pipeline_tasks.sync_cricbuzz_live,
        'sync_completed_matches': pipeline_tasks.sync_completed_matches,
        'sync_player_stats': pipeline_tasks.sync_player_stats,
        'sync_unified_matches': pipeline_tasks.sync_unified_matches,
        'sync_rapidapi_teams': pipeline_tasks.sync_rapidapi_teams,
        'sync_rapidapi_players': pipeline_tasks.sync_rapidapi_players,
        'sync_rapidapi_team_logos': pipeline_tasks.sync_rapidapi_team_logos,
        'run_model_retraining_pipeline': pipeline_tasks.run_model_retraining_pipeline,
    }

    def post(self, request):
        serializer = PipelineTaskTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = cast(dict[str, Any], serializer.validated_data)

        task_name = validated_data['task_name']
        task = self.task_map[task_name]
        if task_name == 'sync_rapidapi_players' and validated_data.get('team_id'):
            async_result = task.delay(team_id=validated_data['team_id'])
        else:
            async_result = task.delay()
        return Response(
            {
                'status': 'queued',
                'task_name': task_name,
                'task_id': async_result.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class SystemMetricsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        payload = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'live_matches': Match.objects.filter(status='live').count(),
            'queued_predictions': PredictionJob.objects.filter(status='pending').count(),
            'processing_predictions': PredictionJob.objects.filter(status='processing').count(),
            'failed_predictions': PredictionJob.objects.filter(status='failed').count(),
            'completed_predictions': PredictionJob.objects.filter(status='complete').count(),
        }
        serializer = SystemMetricsSerializer(payload)
        return Response(serializer.data)


class AdminPredictionJobsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        ordering = _get_prediction_jobs_ordering(request)
        queryset = PredictionJob.objects.select_related('match', 'requested_by').order_by(ordering, '-id')

        status_param = request.query_params.get('status')
        prediction_type = request.query_params.get('prediction_type')
        search = request.query_params.get('search')

        if status_param:
            queryset = queryset.filter(status=status_param)
        if prediction_type in {'pre_match', 'live'}:
            queryset = queryset.filter(prediction_type=prediction_type)
        if search:
            queryset = queryset.filter(match__name__icontains=search)

        paginator = AdminPredictionJobsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is None:
            page = list(queryset)
        serializer = AdminPredictionJobSerializer([_serialize_prediction_job(job) for job in page], many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminPredictionBulkActionView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request):
        serializer = AdminPredictionBulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = cast(dict[str, Any], serializer.validated_data)

        action = str(validated_data['action'])
        job_ids = list(dict.fromkeys(validated_data['job_ids']))
        current_over = validated_data.get('current_over')
        current_score = str(validated_data.get('current_score', ''))

        jobs = PredictionJob.objects.filter(id__in=job_ids)
        jobs_by_id = {int(getattr(job, 'pk', 0) or 0): job for job in jobs}

        results = []
        processed = 0
        skipped = 0

        for job_id in job_ids:
            job = jobs_by_id.get(job_id)
            if not job:
                skipped += 1
                results.append({'id': job_id, 'status': 'skipped', 'reason': 'not_found'})
                continue

            if action == 'cancel':
                if job.status not in {'pending', 'processing'}:
                    skipped += 1
                    results.append({'id': int(getattr(job, 'pk', 0) or 0), 'status': 'skipped', 'reason': 'invalid_status'})
                    continue

                if job.celery_task_id:
                    try:
                        celery_app.control.revoke(job.celery_task_id, terminate=True)
                    except Exception:
                        pass

                job.status = 'failed'
                job.error_message = 'Canceled by admin'
                job.completed_at = timezone.now()
                job.save(update_fields=['status', 'error_message', 'completed_at'])
                processed += 1
                results.append({'id': int(getattr(job, 'pk', 0) or 0), 'status': 'processed'})
                continue

            if job.status != 'failed':
                skipped += 1
                results.append({'id': int(getattr(job, 'pk', 0) or 0), 'status': 'skipped', 'reason': 'invalid_status'})
                continue

            job.status = 'pending'
            job.error_message = ''
            job.completed_at = None
            job.save(update_fields=['status', 'error_message', 'completed_at'])

            job_pk = int(getattr(job, 'pk', 0) or 0)
            task_result = celery_app.send_task('apps.predictions.tasks.process_prediction_job', [job_pk, current_over, current_score])
            job.celery_task_id = str(task_result.id)
            job.save(update_fields=['celery_task_id'])

            processed += 1
            results.append({'id': job_pk, 'status': 'processed', 'task_id': job.celery_task_id})

        return Response(
            {
                'detail': 'Bulk action processed',
                'action': action,
                'requested': len(job_ids),
                'processed': processed,
                'skipped': skipped,
                'results': results,
            }
        )


class AdminPredictionJobDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, job_id: int):
        job = PredictionJob.objects.select_related('match', 'requested_by', 'result__team1', 'result__team2').filter(id=job_id).first()
        if not job:
            return Response({'detail': 'Prediction job not found'}, status=status.HTTP_404_NOT_FOUND)

        payload = _serialize_prediction_job(job)
        result = getattr(job, 'result', None)
        payload['result'] = None
        if result:
            payload['result'] = {
                'team1': result.team1.name if result.team1 else '',
                'team2': result.team2.name if result.team2 else '',
                'team1_win_probability': result.team1_win_probability,
                'team2_win_probability': result.team2_win_probability,
                'draw_probability': result.draw_probability,
                'confidence_score': result.confidence_score,
                'current_over': result.current_over,
                'current_score': result.current_score,
                'created_at': result.created_at,
            }
        return Response(payload)


class AdminPredictionCancelView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, job_id: int):
        job = PredictionJob.objects.filter(id=job_id).first()
        if not job:
            return Response({'detail': 'Prediction job not found'}, status=status.HTTP_404_NOT_FOUND)

        if job.status not in {'pending', 'processing'}:
            return Response({'detail': 'Only pending/processing jobs can be canceled'}, status=status.HTTP_400_BAD_REQUEST)

        if job.celery_task_id:
            try:
                celery_app.control.revoke(job.celery_task_id, terminate=True)
            except Exception:
                pass

        job.status = 'failed'
        job.error_message = 'Canceled by admin'
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'error_message', 'completed_at'])

        return Response({'detail': 'Prediction job canceled'})


class AdminPredictionRetryView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, job_id: int):
        job = PredictionJob.objects.filter(id=job_id).first()
        if not job:
            return Response({'detail': 'Prediction job not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminPredictionRetrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = cast(dict[str, Any], serializer.validated_data)

        current_over = validated_data.get('current_over')
        current_score = str(validated_data.get('current_score', ''))

        job.status = 'pending'
        job.error_message = ''
        job.completed_at = None
        job.save(update_fields=['status', 'error_message', 'completed_at'])

        job_pk = int(getattr(job, 'pk', 0) or 0)
        task_result = celery_app.send_task('apps.predictions.tasks.process_prediction_job', [job_pk, current_over, current_score])
        job.celery_task_id = str(task_result.id)
        job.save(update_fields=['celery_task_id'])

        return Response({'detail': 'Prediction job retry queued', 'task_id': job.celery_task_id}, status=status.HTTP_202_ACCEPTED)
