from django.test import TestCase
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from apps.matches.models import Match, MatchScorecard, Team, Venue


class MatchesApiTests(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.team1 = Team.objects.create(name='India')
		self.team2 = Team.objects.create(name='Australia')
		self.team3 = Team.objects.create(name='England')
		self.team4 = Team.objects.create(name='Mumbai Indians')
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
		self.domestic_match = Match.objects.create(
			name='Mumbai Indians vs England',
			team1=self.team4,
			team2=self.team3,
			status='complete',
			format='odi',
			category='domestic',
			match_date='2026-03-19',
		)
		self.favorite_upcoming = Match.objects.create(
			name='India vs Mumbai Indians',
			team1=self.team1,
			team2=self.team4,
			status='upcoming',
			format='t20',
			category='franchise',
			match_date='2026-03-22',
		)
		self.non_favorite_upcoming = Match.objects.create(
			name='Australia vs England',
			team1=self.team2,
			team2=self.team3,
			status='upcoming',
			format='t20',
			category='international',
			match_date='2026-03-22',
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

	def test_matches_list_filters_by_match_type_alias(self):
		response = self.client.get('/api/v1/matches/?status=complete&match_type=internal')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['count'], 1)
		self.assertEqual(response.data['results'][0]['id'], self.domestic_match.id)

	def test_matches_list_recommendation_ranks_favorite_team_first(self):
		response = self.client.get(f'/api/v1/matches/?status=upcoming&recommendation=true&favorite_team_ids={self.team1.id}')
		self.assertEqual(response.status_code, 200)
		self.assertGreaterEqual(response.data['count'], 2)
		returned_ids = [item['id'] for item in response.data['results']]
		self.assertIn(self.favorite_upcoming.id, returned_ids)
		self.assertIn(self.non_favorite_upcoming.id, returned_ids)
		self.assertEqual(response.data['results'][0]['id'], self.favorite_upcoming.id)

	def test_matches_list_recommendation_prefers_format_affinity_for_non_favorites(self):
		today = timezone.now().date()
		# Build ODI affinity from favorite-team completed matches.
		for offset in range(1, 4):
			Match.objects.create(
				name=f'India ODI recent {offset}',
				team1=self.team1,
				team2=self.team3,
				status='complete',
				format='odi',
				category='international',
				winner=self.team1,
				match_date=today - timedelta(days=offset),
			)

		odi_candidate = Match.objects.create(
			name='Australia vs England ODI Candidate',
			team1=self.team2,
			team2=self.team3,
			status='upcoming',
			format='odi',
			category='international',
			match_date=today + timedelta(days=5),
		)
		t20_candidate = Match.objects.create(
			name='Australia vs England T20 Candidate',
			team1=self.team2,
			team2=self.team3,
			status='upcoming',
			format='t20',
			category='international',
			match_date=today + timedelta(days=5),
		)

		response = self.client.get(f'/api/v1/matches/?status=upcoming&recommendation=true&favorite_team_ids={self.team1.id}')
		self.assertEqual(response.status_code, 200)
		ordered_ids = [item['id'] for item in response.data['results']]
		self.assertIn(odi_candidate.id, ordered_ids)
		self.assertIn(t20_candidate.id, ordered_ids)
		self.assertLess(ordered_ids.index(odi_candidate.id), ordered_ids.index(t20_candidate.id))

	def test_matches_list_recommendation_prefers_nearer_upcoming_match(self):
		today = timezone.now().date()
		near_match = Match.objects.create(
			name='India vs Australia Near',
			team1=self.team1,
			team2=self.team2,
			status='upcoming',
			format='odi',
			category='international',
			match_date=today + timedelta(days=1),
		)
		far_match = Match.objects.create(
			name='India vs Australia Far',
			team1=self.team1,
			team2=self.team2,
			status='upcoming',
			format='odi',
			category='international',
			match_date=today + timedelta(days=20),
		)

		response = self.client.get(f'/api/v1/matches/?status=upcoming&recommendation=true&favorite_team_ids={self.team1.id}')
		self.assertEqual(response.status_code, 200)
		ordered_ids = [item['id'] for item in response.data['results']]
		self.assertIn(near_match.id, ordered_ids)
		self.assertIn(far_match.id, ordered_ids)
		self.assertLess(ordered_ids.index(near_match.id), ordered_ids.index(far_match.id))
