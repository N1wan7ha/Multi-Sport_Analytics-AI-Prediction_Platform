from django.test import TestCase
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.matches.models import Match, MatchScorecard, Team, Venue


class MatchesApiTests(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.team1 = Team.objects.create(name='India')
		self.team2 = Team.objects.create(name='Australia')
		self.team3 = Team.objects.create(name='England')
		self.venue = Venue.objects.create(name='Wankhede Stadium')

		self.live_match = Match.objects.create(
			name='India vs Australia',
			team1=self.team1,
			team2=self.team2,
			venue=self.venue,
			status='live',
			format='odi',
			category='international',
			match_date='2026-03-21',
		)
		self.completed_match = Match.objects.create(
			name='India vs England',
			team1=self.team1,
			team2=self.team3,
			status='complete',
			format='t20',
			category='international',
			match_date='2026-03-20',
		)

	def test_matches_list_filters_status_and_date(self):
		response = self.client.get('/api/v1/matches/?status=live&match_date=2026-03-21')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['count'], 1)
		self.assertEqual(response.data['results'][0]['id'], self.live_match.id)

	def test_live_matches_endpoint(self):
		response = self.client.get('/api/v1/matches/live/')
		self.assertEqual(response.status_code, 200)
		self.assertGreaterEqual(response.data['count'], 1)
		returned_ids = [item['id'] for item in response.data['results']]
		self.assertIn(self.live_match.id, returned_ids)
		self.assertTrue(all(item['status'] == 'live' for item in response.data['results']))

	def test_match_detail_includes_scorecards(self):
		MatchScorecard.objects.create(
			match=self.completed_match,
			innings_number=1,
			batting_team=self.team1,
			total_runs=250,
			total_wickets=8,
			total_overs=50,
			run_rate=5.0,
			batting_data=[],
			bowling_data=[],
		)

		response = self.client.get(f'/api/v1/matches/{self.completed_match.id}/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data['scorecards']), 1)
