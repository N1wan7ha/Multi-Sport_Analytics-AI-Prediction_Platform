from django.test import TestCase
from rest_framework.test import APIClient

from apps.matches.models import Match, Team
from apps.players.models import Player, PlayerMatchStats


class PlayersApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.team = Team.objects.create(name='India')
		self.opp = Team.objects.create(name='England')
		self.player = Player.objects.create(name='Virat Kohli', full_name='Virat Kohli', country='India', team=self.team)
		self.match = Match.objects.create(
			name='India vs England',
			team1=self.team,
			team2=self.opp,
			status='complete',
			format='odi',
			category='international',
			match_date='2026-03-10',
		)
		PlayerMatchStats.objects.create(
			player=self.player,
			match=self.match,
			innings_number=1,
			runs_scored=88,
			balls_faced=95,
			fours=8,
			sixes=1,
			strike_rate=92.6,
		)

	def test_players_search(self):
		response = self.client.get('/api/v1/players/?search=Virat')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['count'], 1)
		self.assertEqual(response.data['results'][0]['name'], 'Virat Kohli')

	def test_player_detail_includes_recent_stats(self):
		response = self.client.get(f'/api/v1/players/{self.player.id}/')
		self.assertEqual(response.status_code, 200)
		self.assertIn('recent_stats', response.data)
		self.assertEqual(len(response.data['recent_stats']), 1)
		self.assertEqual(response.data['recent_stats'][0]['runs_scored'], 88)
