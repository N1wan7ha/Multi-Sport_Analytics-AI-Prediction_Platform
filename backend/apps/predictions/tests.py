from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import Mock, patch

from apps.matches.models import Match, Team
from apps.predictions.models import PredictionJob
from apps.predictions.tasks import schedule_live_predictions


User = get_user_model()


class PredictionsApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.user = User.objects.create_user(
			email='phase2@test.dev',
			username='phase2user',
			password='strongpass123',
		)
		self.client.force_authenticate(user=self.user)

		self.team1 = Team.objects.create(name='India')
		self.team2 = Team.objects.create(name='England')
		self.match = Match.objects.create(
			name='India vs England',
			team1=self.team1,
			team2=self.team2,
			status='upcoming',
			format='odi',
			category='international',
			match_date='2026-05-01',
		)

	def test_create_prediction_job_returns_result_payload(self):
		response = self.client.post('/api/v1/predictions/', {
			'match': self.match.id,
			'prediction_type': 'pre_match',
		}, format='json')
		self.assertEqual(response.status_code, 201)
		self.assertIn('result', response.data)
		self.assertIn('team1_win_probability', response.data['result'])
		self.assertIn('feature_snapshot', response.data['result'])
		self.assertIn('model_kind', response.data['result']['feature_snapshot'])

	def test_prediction_detail_and_latest_for_match(self):
		create_response = self.client.post('/api/v1/predictions/', {
			'match': self.match.id,
			'prediction_type': 'pre_match',
		}, format='json')
		job_id = create_response.data['id']

		detail_response = self.client.get(f'/api/v1/predictions/{job_id}/')
		self.assertEqual(detail_response.status_code, 200)
		self.assertEqual(detail_response.data['match'], self.match.id)

		latest_response = self.client.get(f'/api/v1/predictions/match/{self.match.id}/')
		self.assertEqual(latest_response.status_code, 200)
		self.assertEqual(latest_response.data['id'], job_id)

	def test_live_prediction_requires_current_over(self):
		response = self.client.post('/api/v1/predictions/', {
			'match': self.match.id,
			'prediction_type': 'live',
			'current_score': '92/2',
		}, format='json')
		self.assertEqual(response.status_code, 400)
		self.assertIn('current_over', response.data)

	def test_live_prediction_persists_live_context_and_latest_filter(self):
		self.match.status = 'live'
		self.match.save(update_fields=['status'])

		response = self.client.post('/api/v1/predictions/', {
			'match': self.match.id,
			'prediction_type': 'live',
			'current_over': 14,
			'current_score': '122/3',
		}, format='json')
		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data['prediction_type'], 'live')

		result = response.data.get('result') or {}
		self.assertEqual(result.get('current_over'), 14)
		self.assertEqual(result.get('current_score'), '122/3')

		latest_live = self.client.get(f'/api/v1/predictions/match/{self.match.id}/?prediction_type=live')
		self.assertEqual(latest_live.status_code, 200)
		self.assertEqual(latest_live.data['prediction_type'], 'live')


@override_settings(LIVE_PREDICTION_OVER_STEP=2)
class LivePredictionSchedulerTests(TestCase):
	def setUp(self):
		cache.clear()
		self.team1 = Team.objects.create(name='Australia')
		self.team2 = Team.objects.create(name='Pakistan')
		self.match = Match.objects.create(
			name='Australia vs Pakistan',
			team1=self.team1,
			team2=self.team2,
			status='live',
			format='t20',
			category='international',
			match_date='2026-06-01',
			raw_data={
				'currentOver': '12.3',
				'currentScore': '110/2',
			},
		)

	@patch('apps.predictions.tasks.celery_app.send_task')
	def test_schedule_live_predictions_creates_job_when_over_step_reached(self, mock_send_task):
		mock_send_task.return_value = Mock(id='celery-live-1')

		summary = schedule_live_predictions()

		self.assertEqual(summary['scheduled'], 1)
		self.assertEqual(PredictionJob.objects.filter(match=self.match, prediction_type='live').count(), 1)
		self.assertEqual(cache.get(f'predictions:live:last_trigger_over:{self.match.id}'), 12)
		mock_send_task.assert_called_once()

	@patch('apps.predictions.tasks.celery_app.send_task')
	def test_schedule_live_predictions_skips_when_over_step_not_reached(self, mock_send_task):
		cache.set(f'predictions:live:last_trigger_over:{self.match.id}', 12, timeout=60)
		self.match.raw_data = {
			'currentOver': '13.1',
			'currentScore': '118/3',
		}
		self.match.save(update_fields=['raw_data'])

		summary = schedule_live_predictions()

		self.assertEqual(summary['scheduled'], 0)
		self.assertEqual(summary['skipped_over_step'], 1)
		self.assertEqual(PredictionJob.objects.filter(match=self.match, prediction_type='live').count(), 0)
		mock_send_task.assert_not_called()
