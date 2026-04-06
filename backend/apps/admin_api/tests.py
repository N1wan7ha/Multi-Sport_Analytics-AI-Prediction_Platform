from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.matches.models import Match, Team
from apps.predictions.models import PredictionJob


User = get_user_model()


class AdminApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@test.dev',
            username='admin-user',
            password='strongpass123',
            role='ADMIN',
        )
        self.user = User.objects.create_user(
            email='user@test.dev',
            username='normal-user',
            password='strongpass123',
            role='USER',
        )

        team1 = Team.objects.create(name='India')
        team2 = Team.objects.create(name='England')
        self.match = Match.objects.create(
            name='India vs England',
            team1=team1,
            team2=team2,
            status='upcoming',
            format='odi',
            category='international',
            match_date='2026-07-01',
        )

    def test_prediction_jobs_admin_only(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/v1/admin/prediction-jobs/')
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/v1/admin/prediction-jobs/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

    def test_prediction_job_detail_returns_payload(self):
        job = PredictionJob.objects.create(
            match=self.match,
            requested_by=self.user,
            prediction_type='pre_match',
            status='pending',
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get(f'/api/v1/admin/prediction-jobs/{job.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], job.id)
        self.assertEqual(response.data['match_id'], self.match.id)

    def test_prediction_jobs_support_sorting(self):
        first_job = PredictionJob.objects.create(
            match=self.match,
            requested_by=self.user,
            prediction_type='live',
            status='processing',
        )
        second_job = PredictionJob.objects.create(
            match=self.match,
            requested_by=self.user,
            prediction_type='pre_match',
            status='failed',
        )

        older_time = timezone.now() - timedelta(hours=3)
        newer_time = timezone.now() - timedelta(hours=1)
        PredictionJob.objects.filter(id=first_job.id).update(requested_at=newer_time)
        PredictionJob.objects.filter(id=second_job.id).update(requested_at=older_time)

        self.client.force_authenticate(self.admin)

        response = self.client.get('/api/v1/admin/prediction-jobs/?sort_by=requested_at&sort_dir=asc')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['id'], second_job.id)

        response = self.client.get('/api/v1/admin/prediction-jobs/?ordering=status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['status'], 'failed')

    @patch('apps.admin_api.views.celery_app.control.revoke')
    def test_cancel_prediction_job(self, revoke_mock):
        job = PredictionJob.objects.create(
            match=self.match,
            requested_by=self.user,
            prediction_type='pre_match',
            status='pending',
            celery_task_id='task-123',
        )

        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/api/v1/admin/prediction-jobs/{job.id}/cancel/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'Prediction job canceled')

        revoke_mock.assert_called_once_with('task-123', terminate=True)
        job.refresh_from_db()
        self.assertEqual(job.status, 'failed')
        self.assertEqual(job.error_message, 'Canceled by admin')

    @patch('apps.admin_api.views.celery_app.send_task')
    def test_retry_prediction_job(self, send_task_mock):
        class Result:
            id = 'retry-task-999'

        send_task_mock.return_value = Result()

        job = PredictionJob.objects.create(
            match=self.match,
            requested_by=self.user,
            prediction_type='pre_match',
            status='failed',
            error_message='Model unavailable',
        )

        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/api/v1/admin/prediction-jobs/{job.id}/retry/', {}, format='json')
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['detail'], 'Prediction job retry queued')

        send_task_mock.assert_called_once_with(
            'apps.predictions.tasks.process_prediction_job',
            [job.id, None, ''],
        )
        job.refresh_from_db()
        self.assertEqual(job.status, 'pending')
        self.assertEqual(job.error_message, '')
        self.assertEqual(job.celery_task_id, 'retry-task-999')

    @patch('apps.admin_api.views.celery_app.control.revoke')
    def test_bulk_cancel_prediction_jobs(self, revoke_mock):
        cancelable = PredictionJob.objects.create(
            match=self.match,
            requested_by=self.user,
            prediction_type='pre_match',
            status='pending',
            celery_task_id='task-a',
        )
        non_cancelable = PredictionJob.objects.create(
            match=self.match,
            requested_by=self.user,
            prediction_type='live',
            status='complete',
        )

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            '/api/v1/admin/prediction-jobs/bulk-action/',
            {'action': 'cancel', 'job_ids': [cancelable.id, non_cancelable.id, 999999]},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['processed'], 1)
        self.assertEqual(response.data['skipped'], 2)

        revoke_mock.assert_called_once_with('task-a', terminate=True)
        cancelable.refresh_from_db()
        self.assertEqual(cancelable.status, 'failed')

    @patch('apps.admin_api.views.celery_app.send_task')
    def test_bulk_retry_prediction_jobs(self, send_task_mock):
        class Result:
            id = 'retry-bulk-task'

        send_task_mock.return_value = Result()

        retryable = PredictionJob.objects.create(
            match=self.match,
            requested_by=self.user,
            prediction_type='pre_match',
            status='failed',
            error_message='Old failure',
        )
        non_retryable = PredictionJob.objects.create(
            match=self.match,
            requested_by=self.user,
            prediction_type='live',
            status='processing',
        )

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            '/api/v1/admin/prediction-jobs/bulk-action/',
            {
                'action': 'retry',
                'job_ids': [retryable.id, non_retryable.id],
                'current_over': 27,
                'current_score': '180/4',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['processed'], 1)
        self.assertEqual(response.data['skipped'], 1)

        send_task_mock.assert_called_once_with(
            'apps.predictions.tasks.process_prediction_job',
            [retryable.id, 27, '180/4'],
        )
        retryable.refresh_from_db()
        self.assertEqual(retryable.status, 'pending')
        self.assertEqual(retryable.error_message, '')
        self.assertEqual(retryable.celery_task_id, 'retry-bulk-task')

    @patch('apps.admin_api.views.pipeline_tasks.sync_rapidapi_players.delay')
    def test_pipeline_trigger_passes_team_id_for_player_sync(self, delay_mock):
        class Result:
            id = 'pipeline-task-123'

        delay_mock.return_value = Result()

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            '/api/v1/admin/pipeline/trigger/',
            {'task_name': 'sync_rapidapi_players', 'team_id': 55},
            format='json',
        )

        self.assertEqual(response.status_code, 202)
        delay_mock.assert_called_once_with(team_id=55)

    @patch('apps.admin_api.views.pipeline_tasks.sync_rapidapi_teams.delay')
    @patch('apps.admin_api.views.pipeline_tasks.sync_rapidapi_team_logos.delay')
    @patch('apps.admin_api.views.pipeline_tasks.sync_rapidapi_players.delay')
    def test_pipeline_bulk_trigger_queues_bundle(self, players_delay_mock, logos_delay_mock, teams_delay_mock):
        class TeamsResult:
            id = 'teams-task-1'

        class LogosResult:
            id = 'logos-task-1'

        class PlayersResult:
            id = 'players-task-1'

        teams_delay_mock.return_value = TeamsResult()
        logos_delay_mock.return_value = LogosResult()
        players_delay_mock.return_value = PlayersResult()

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            '/api/v1/admin/pipeline/trigger-bulk/',
            {'bundle_name': 'rapidapi_catalog', 'team_id': 77},
            format='json',
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['bundle_name'], 'rapidapi_catalog')
        self.assertEqual(response.data['queued_count'], 3)
        self.assertEqual(len(response.data['tasks']), 3)

        teams_delay_mock.assert_called_once_with()
        logos_delay_mock.assert_called_once_with()
        players_delay_mock.assert_called_once_with(team_id=77)

    def test_pipeline_status_includes_endpoint_health(self):
        cache.set(
            'pipeline:endpoint_health:last_success',
            {'live_scores': {'provider': 'rapidapi_livescore6', 'path': '/matches/v2/list-live?Category=cricket', 'at': '2026-03-20T20:00:00Z'}},
        )
        cache.set(
            'pipeline:endpoint_health:history',
            {
                'live_scores': [
                    {'provider': 'rapidapi', 'path': '/cricket-livescores', 'at': '2026-03-20T19:00:00Z'},
                    {'provider': 'rapidapi_livescore6', 'path': '/matches/v2/list-live?Category=cricket', 'at': '2026-03-20T20:00:00Z'},
                ]
            },
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/v1/admin/pipeline/status/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('endpoint_health', response.data)
        self.assertIn('live_scores', response.data['endpoint_health'])
        self.assertIn('endpoint_health_history', response.data)
        self.assertIn('live_scores', response.data['endpoint_health_history'])
        self.assertEqual(len(response.data['endpoint_health_history']['live_scores']), 2)
        self.assertIn('livescore6_endpoint_health', response.data)
        self.assertEqual(response.data['livescore6_endpoint_health']['provider'], 'rapidapi_livescore6')

    @patch('apps.admin_api.views.rank_versions')
    @patch('apps.admin_api.views.select_best_version')
    def test_model_ranking_endpoint_returns_scored_versions(self, best_mock, rank_mock):
        rank_mock.return_value = [
            {
                'version': 'v2.5',
                'model_type': 'sklearn_ensemble',
                'accuracy': 0.83,
                'auc_roc': 0.89,
                'brier_score': 0.16,
                'sample_count': 2400,
                'score': 0.9012,
                'components': {
                    'accuracy_component': 0.3735,
                    'auc_component': 0.4005,
                    'brier_component': 0.084,
                    'quality_bonus': 0.1,
                    'size_bonus': 0.048,
                },
            }
        ]
        best_mock.return_value = 'v2.5'

        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/v1/admin/models/ranking/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['selected_version'], 'v2.5')
        self.assertEqual(response.data['total_versions'], 1)
        self.assertEqual(response.data['ranked_versions'][0]['version'], 'v2.5')
        self.assertIn('selection_reason', response.data)
