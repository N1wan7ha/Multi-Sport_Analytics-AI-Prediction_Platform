from django.test import TestCase
from rest_framework.test import APIClient

from apps.matches.models import Match, Team
from apps.series.models import Series


class SeriesApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.team1 = Team.objects.create(name='India')
		self.team2 = Team.objects.create(name='Australia')
		self.series = Series.objects.create(cricapi_id='s1', name='Border Trophy')
		Match.objects.create(
			name='India vs Australia - 1st ODI',
			team1=self.team1,
			team2=self.team2,
			status='upcoming',
			format='odi',
			category='international',
			match_date='2026-04-01',
			raw_data={'seriesName': 'Border Trophy', 'seriesId': 's1'},
		)

	def test_series_list(self):
		response = self.client.get('/api/v1/series/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['count'], 1)

	def test_series_matches_endpoint(self):
		response = self.client.get(f'/api/v1/series/{self.series.id}/matches/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['count'], 1)
		self.assertEqual(response.data['results'][0]['name'], 'India vs Australia - 1st ODI')
