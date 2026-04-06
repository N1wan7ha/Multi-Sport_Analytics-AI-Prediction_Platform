from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase, override_settings
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.matches.models import Team, Match
from apps.players.models import Player
from apps.predictions.models import PredictionJob
from apps.predictions.models import PredictionResult
from .models import NotificationDispatch, UserFavouritePlayer, UserFavouriteTeam
from .tasks import send_match_start_notifications, send_prediction_ready_notifications


User = get_user_model()


class AccountsApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.user = User.objects.create_user(
			email='accounts@test.dev',
			username='accounts-user',
			password='strongpass123',
		)
		self.client.force_authenticate(self.user)
		self.team1 = Team.objects.create(name='India')
		self.team2 = Team.objects.create(name='Australia')
		self.player1 = Player.objects.create(name='Virat Kohli', team=self.team1, role='batsman')
		self.player2 = Player.objects.create(name='Pat Cummins', team=self.team2, role='bowler')

	def test_profile_update_supports_favourite_team_ids(self):
		response = self.client.patch('/api/v1/auth/profile/', {
			'bio': 'Cricket fan',
			'favourite_team_ids': [self.team1.id, self.team2.id],
		}, format='json')

		self.assertEqual(response.status_code, 200)
		favourites = response.data.get('favourite_teams', [])
		self.assertEqual(len(favourites), 2)
		favourite_names = {team['name'] for team in favourites}
		self.assertSetEqual(favourite_names, {'India', 'Australia'})

	def test_profile_update_supports_favourite_player_ids(self):
		response = self.client.patch('/api/v1/auth/profile/', {
			'favourite_player_ids': [self.player1.id, self.player2.id],
		}, format='json')

		self.assertEqual(response.status_code, 200)
		favourites = response.data.get('favourite_players', [])
		self.assertEqual(len(favourites), 2)
		favourite_names = {player['name'] for player in favourites}
		self.assertSetEqual(favourite_names, {'Virat Kohli', 'Pat Cummins'})
		self.assertEqual(UserFavouritePlayer.objects.filter(user=self.user).count(), 2)

	def test_profile_update_rejects_more_than_five_favourite_teams(self):
		team_ids = []
		for index in range(6):
			team_ids.append(Team.objects.create(name=f'Team {index}').id)

		response = self.client.patch('/api/v1/auth/profile/', {
			'favourite_team_ids': team_ids,
		}, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertIn('favourite_team_ids', response.data)

	def test_profile_update_rejects_more_than_eleven_favourite_players(self):
		player_ids = []
		for index in range(12):
			player_ids.append(Player.objects.create(name=f'Player {index}', team=self.team1, role='batsman').id)

		response = self.client.patch('/api/v1/auth/profile/', {
			'favourite_player_ids': player_ids,
		}, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertIn('favourite_player_ids', response.data)

	def test_profile_update_rejects_duplicate_favourite_players(self):
		response = self.client.patch('/api/v1/auth/profile/', {
			'favourite_player_ids': [self.player1.id, self.player1.id],
		}, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertIn('favourite_player_ids', response.data)

	def test_prediction_history_returns_user_jobs_only(self):
		other_user = User.objects.create_user(
			email='other@test.dev',
			username='other-user',
			password='strongpass123',
		)
		match = Match.objects.create(
			name='India vs Australia',
			team1=self.team1,
			team2=self.team2,
			status='upcoming',
			format='odi',
			category='international',
			match_date='2026-07-01',
		)
		own_job = PredictionJob.objects.create(
			match=match,
			requested_by=self.user,
			prediction_type='pre_match',
			status='complete',
		)
		PredictionJob.objects.create(
			match=match,
			requested_by=other_user,
			prediction_type='pre_match',
			status='complete',
		)

		response = self.client.get('/api/v1/auth/prediction-history/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['count'], 1)
		self.assertEqual(response.data['results'][0]['id'], own_job.id)

	def test_team_options_requires_auth_and_returns_sorted_teams(self):
		anon = APIClient()
		anon_response = anon.get('/api/v1/auth/team-options/')
		self.assertEqual(anon_response.status_code, 401)

		response = self.client.get('/api/v1/auth/team-options/')
		self.assertEqual(response.status_code, 200)
		self.assertGreaterEqual(len(response.data), 2)
		self.assertLessEqual(response.data[0]['name'], response.data[-1]['name'])

	def test_team_options_supports_query_filter(self):
		Team.objects.create(name='England', logo_url='https://example.test/logo-england.png')

		response = self.client.get('/api/v1/auth/team-options/?q=Ind')
		self.assertEqual(response.status_code, 200)
		self.assertGreaterEqual(len(response.data), 1)
		self.assertTrue(all('ind' in row['name'].lower() for row in response.data))

	def test_team_options_include_logo_url_field(self):
		self.team1.logo_url = 'https://example.test/logo-india.png'
		self.team1.save(update_fields=['logo_url'])

		response = self.client.get('/api/v1/auth/team-options/')
		self.assertEqual(response.status_code, 200)
		india_row = next((row for row in response.data if row['id'] == self.team1.id), None)
		self.assertIsNotNone(india_row)
		self.assertEqual(india_row['logo_url'], 'https://example.test/logo-india.png')

	def test_player_options_supports_query_and_auth(self):
		anon = APIClient()
		anon_response = anon.get('/api/v1/auth/player-options/')
		self.assertEqual(anon_response.status_code, 401)

		response = self.client.get('/api/v1/auth/player-options/?q=Virat')
		self.assertEqual(response.status_code, 200)
		self.assertGreaterEqual(len(response.data), 1)
		self.assertTrue(any('virat' in row['name'].lower() for row in response.data))

	@override_settings(GOOGLE_CLIENT_ID='test-google-client-id')
	@patch('apps.accounts.views.google_id_token.verify_oauth2_token')
	def test_google_auth_creates_verified_user_and_returns_jwt(self, verify_token_mock):
		verify_token_mock.return_value = {
			'email': 'google-user@test.dev',
			'email_verified': True,
			'name': 'Google User',
		}

		response = self.client.post('/api/v1/auth/google/', {'token': 'mock-google-token'}, format='json')
		self.assertEqual(response.status_code, 200)
		self.assertIn('access', response.data)
		self.assertIn('refresh', response.data)

		user = User.objects.get(email='google-user@test.dev')
		self.assertTrue(user.email_verified)

	@override_settings(GOOGLE_CLIENT_ID='test-google-client-id')
	@patch('apps.accounts.views.google_id_token.verify_oauth2_token')
	def test_google_auth_rejects_unverified_google_email(self, verify_token_mock):
		verify_token_mock.return_value = {
			'email': 'google-unverified@test.dev',
			'email_verified': False,
			'name': 'Unverified User',
		}

		response = self.client.post('/api/v1/auth/google/', {'token': 'mock-google-token'}, format='json')
		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.data['detail'], 'Google email is not verified')

	def test_confirm_email_verification_marks_user_verified(self):
		user = User.objects.create_user(
			email='verify@test.dev',
			username='verify-user',
			password='strongpass123',
			email_verified=False,
		)
		token = signing.dumps({'user_id': user.id, 'email': user.email}, salt='accounts-email-verify')

		response = self.client.post('/api/v1/auth/verify-email/confirm/', {'token': token}, format='json')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['detail'], 'Email verified successfully')

		user.refresh_from_db()
		self.assertTrue(user.email_verified)

	def test_resend_email_verification_sends_email_for_authenticated_user(self):
		user = User.objects.create_user(
			email='resend@test.dev',
			username='resend-user',
			password='strongpass123',
			email_verified=False,
		)
		self.client.force_authenticate(user)

		response = self.client.post('/api/v1/auth/verify-email/', {}, format='json')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['detail'], 'Verification email sent')
		self.assertEqual(len(mail.outbox), 1)


class NotificationTaskTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			email='notify@test.dev',
			username='notify-user',
			password='strongpass123',
		)
		self.team1 = Team.objects.create(name='Sri Lanka')
		self.team2 = Team.objects.create(name='New Zealand')

	def test_send_match_start_notifications_dispatches_once(self):
		UserFavouriteTeam.objects.create(user=self.user, team=self.team1)
		match = Match.objects.create(
			name='Sri Lanka vs New Zealand',
			team1=self.team1,
			team2=self.team2,
			status='upcoming',
			format='odi',
			category='international',
			match_date='2026-08-01',
			match_datetime=timezone.now() + timezone.timedelta(minutes=20),
		)

		result = send_match_start_notifications()
		self.assertEqual(result['sent'], 1)
		self.assertEqual(len(mail.outbox), 1)
		self.assertTrue(NotificationDispatch.objects.filter(user=self.user, match=match, notification_type='match_start').exists())

		# Dedupe check
		result_again = send_match_start_notifications()
		self.assertEqual(result_again['sent'], 0)

	def test_send_prediction_ready_notifications_dispatches_once(self):
		match = Match.objects.create(
			name='Sri Lanka vs New Zealand',
			team1=self.team1,
			team2=self.team2,
			status='upcoming',
			format='odi',
			category='international',
			match_date='2026-08-01',
		)
		job = PredictionJob.objects.create(
			match=match,
			requested_by=self.user,
			prediction_type='pre_match',
			status='complete',
		)
		PredictionResult.objects.create(
			job=job,
			team1=self.team1,
			team2=self.team2,
			team1_win_probability=0.55,
			team2_win_probability=0.45,
			draw_probability=0.0,
			confidence_score=0.77,
		)

		result = send_prediction_ready_notifications()
		self.assertEqual(result['sent'], 1)
		self.assertEqual(len(mail.outbox), 1)
		self.assertTrue(NotificationDispatch.objects.filter(user=self.user, prediction_job=job, notification_type='prediction_ready').exists())

		result_again = send_prediction_ready_notifications()
		self.assertEqual(result_again['sent'], 0)
