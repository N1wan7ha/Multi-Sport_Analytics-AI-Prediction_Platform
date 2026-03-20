from django.test import TestCase
from rest_framework.test import APIClient

from apps.matches.models import Match, Team
from apps.players.models import Player, PlayerMatchStats


class AnalyticsApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.india = Team.objects.create(name='India')
		self.england = Team.objects.create(name='England')

		self.match = Match.objects.create(
			name='India vs England',
			team1=self.india,
			team2=self.england,
			status='complete',
			winner=self.india,
			format='odi',
			category='international',
			match_date='2026-03-01',
		)

		self.player = Player.objects.create(name='Rohit Sharma', team=self.india)
		PlayerMatchStats.objects.create(
			player=self.player,
			match=self.match,
			innings_number=1,
			runs_scored=75,
			balls_faced=80,
			strike_rate=93.75,
			wickets_taken=0,
			economy=0,
		)

	def test_team_analytics_endpoint(self):
		response = self.client.get('/api/v1/analytics/team/India/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['wins'], 1)
		self.assertEqual(response.data['losses'], 0)

	def test_player_analytics_endpoint(self):
		response = self.client.get(f'/api/v1/analytics/player/{self.player.id}/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['total_runs'], 75)
		self.assertEqual(response.data['matches'], 1)
