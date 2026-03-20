from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.matches.models import Match, Team


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
