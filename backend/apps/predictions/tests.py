from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import Mock, patch

from apps.matches.models import Match, Team
from apps.players.models import Player, PlayerMatchStats
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

		self.team1, _ = Team.objects.get_or_create(name='India')
		self.team2, _ = Team.objects.get_or_create(name='England')
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
		self.assertIn('pre_match_projection', response.data['result'])

	def test_pre_match_projection_includes_gender_segment(self):
		self.match.name = 'India Women vs England Women'
		self.match.save(update_fields=['name'])

		response = self.client.post('/api/v1/predictions/', {
			'match': self.match.id,
			'prediction_type': 'pre_match',
		}, format='json')

		self.assertEqual(response.status_code, 201)
		projection = (response.data.get('result') or {}).get('pre_match_projection') or {}
		self.assertEqual(projection.get('gender_segment'), 'women')

	def test_prediction_create_requires_authentication(self):
		anon = APIClient()
		response = anon.post('/api/v1/predictions/', {
			'match': self.match.id,
			'prediction_type': 'pre_match',
		}, format='json')
		self.assertEqual(response.status_code, 401)

	def test_prediction_rejects_non_live_or_upcoming_match(self):
		self.match.status = 'complete'
		self.match.save(update_fields=['status'])

		response = self.client.post('/api/v1/predictions/', {
			'match': self.match.id,
			'prediction_type': 'pre_match',
		}, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertIn('match', response.data)

	def test_live_prediction_requires_live_match_status(self):
		response = self.client.post('/api/v1/predictions/', {
			'match': self.match.id,
			'prediction_type': 'live',
			'current_over': 5,
		}, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertIn('prediction_type', response.data)

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

	def test_live_prediction_allows_missing_current_over(self):
		self.match.status = 'live'
		self.match.save(update_fields=['status'])

		response = self.client.post('/api/v1/predictions/', {
			'match': self.match.id,
			'prediction_type': 'live',
			'current_score': '92/2',
		}, format='json')
		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data['prediction_type'], 'live')

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

	def test_live_prediction_returns_explainability_with_historical_player_fallback(self):
		self.match.status = 'live'
		self.match.current_batters = []
		self.match.current_bowlers = []
		self.match.save(update_fields=['status', 'current_batters', 'current_bowlers'])

		hist_match = Match.objects.create(
			name='India vs England Historic',
			team1=self.team1,
			team2=self.team2,
			status='complete',
			format='odi',
			category='international',
			match_date='2025-05-01',
		)

		t1_player = Player.objects.create(name='India Batter', team=self.team1)
		t2_player = Player.objects.create(name='England Bowler', team=self.team2)

		PlayerMatchStats.objects.create(
			player=t1_player,
			match=hist_match,
			innings_number=1,
			runs_scored=70,
			strike_rate=110.0,
			wickets_taken=0,
			economy=0,
		)
		PlayerMatchStats.objects.create(
			player=t2_player,
			match=hist_match,
			innings_number=1,
			runs_scored=5,
			strike_rate=60.0,
			wickets_taken=2,
			economy=4.5,
		)

		response = self.client.post('/api/v1/predictions/', {
			'match': self.match.id,
			'prediction_type': 'live',
			'current_over': 12,
			'current_score': '98/3',
		}, format='json')

		self.assertEqual(response.status_code, 201)
		result = response.data.get('result') or {}
		self.assertIn('explainability', result)
		explainability = result.get('explainability') or {}
		self.assertIn('team_strength_score', explainability)
		self.assertIn('player_impact_score', explainability)
		self.assertIn('momentum_score', explainability)
		self.assertIn('player_impact_score', result)


@override_settings(LIVE_PREDICTION_OVER_STEP=2)
class LivePredictionSchedulerTests(TestCase):
	def setUp(self):
		cache.clear()
		self.team1, _ = Team.objects.get_or_create(name='Australia')
		self.team2, _ = Team.objects.get_or_create(name='Pakistan')
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
