from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.data_pipeline import tasks
from apps.data_pipeline.normalizers import (
    merge_and_dedupe_matches,
    normalize_cricapi_match,
    normalize_cricbuzz_live_match,
)
from apps.matches.models import Match, MatchScorecard, Team
from apps.players.models import PlayerMatchStats


class NormalizerTests(TestCase):
    def test_normalize_cricapi_match_maps_status_and_format(self):
        row = {
            'id': 'abc123',
            'name': 'India vs Australia',
            'matchType': 'T20I',
            'status': 'India won by 5 wickets',
            'teams': ['India', 'Australia'],
            'date': '2026-03-19',
        }

        normalized = normalize_cricapi_match(row)

        self.assertEqual(normalized.source_id, 'abc123')
        self.assertEqual(normalized.format, 't20')
        self.assertEqual(normalized.status, 'complete')
        self.assertEqual(normalized.team1_name, 'India')
        self.assertEqual(normalized.team2_name, 'Australia')

    def test_merge_and_dedupe_matches_combines_two_sources(self):
        cricapi = normalize_cricapi_match(
            {
                'id': '100',
                'name': 'India vs Australia',
                'matchType': 'ODI',
                'status': 'scheduled',
                'teams': ['India', 'Australia'],
                'date': '2026-03-20',
            }
        )
        cricbuzz = normalize_cricbuzz_live_match(
            {
                'matchId': '900',
                'team1': {'teamName': 'India'},
                'team2': {'teamName': 'Australia'},
                'matchFormat': 'ODI',
                'startDate': '1773964800000',
            }
        )

        merged = merge_and_dedupe_matches([cricapi, cricbuzz])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].status, 'live')
        self.assertIn('cricapi', merged[0].sources)
        self.assertIn('cricbuzz', merged[0].sources)


class PipelineTaskIntegrationTests(TestCase):
    def setUp(self):
        """Clear match data before each test to ensure isolation."""
        from apps.matches.models import Match, Team, Venue
        Match.objects.all().delete()
        Team.objects.all().delete()
        Venue.objects.all().delete()

    @patch('apps.data_pipeline.tasks._cricapi_get')
    def test_sync_current_matches_writes_match_rows(self, mock_cricapi_get):
        mock_cricapi_get.return_value = {
            'status': 'success',
            'data': [
                {
                    'id': 'm1',
                    'name': 'India vs England',
                    'matchType': 'ODI',
                    'status': 'scheduled',
                    'teams': ['India', 'England'],
                    'date': '2026-03-20',
                    'venue': 'Wankhede Stadium',
                }
            ],
        }

        result = tasks.sync_current_matches.run()

        self.assertEqual(result['synced'], 1)
        self.assertEqual(Match.objects.count(), 1)
        created = Match.objects.get(cricapi_id='m1')
        self.assertEqual(created.status, 'upcoming')
        self.assertEqual(created.team1.name, 'India')
        self.assertEqual(created.team2.name, 'England')
        self.assertIsNotNone(cache.get('pipeline:current_matches:last_sync_at'))

    @patch('apps.data_pipeline.tasks._cricbuzz_get')
    def test_sync_cricbuzz_live_writes_live_match_rows(self, mock_cricbuzz_get):
        mock_cricbuzz_get.return_value = {
            'typeMatches': [
                {
                    'matchType': 'League',
                    'seriesMatches': [
                        {
                            'seriesAdWrapper': {
                                'seriesName': 'Indian Premier League',
                                'matches': [
                                    {
                                        'matchInfo': {
                                            'matchId': 'cbz1',
                                            'team1': {'teamName': 'MI'},
                                            'team2': {'teamName': 'CSK'},
                                            'matchFormat': 'T20',
                                            'startDate': '1773964800000',
                                            'venueInfo': {'ground': 'Eden Gardens'},
                                        }
                                    }
                                ],
                            }
                        }
                    ],
                }
            ]
        }

        result = tasks.sync_cricbuzz_live.run()

        self.assertEqual(result['synced'], 1)
        self.assertEqual(Match.objects.count(), 1)
        created = Match.objects.get(cricbuzz_id='cbz1')
        self.assertEqual(created.status, 'live')
        self.assertEqual(created.category, 'franchise')
        self.assertIsNotNone(cache.get('pipeline:live_matches:last_sync_at'))

    @patch('apps.data_pipeline.tasks._cricapi_get')
    def test_sync_player_stats_writes_scorecards_and_player_stats(self, mock_cricapi_get):
        team1 = Team.objects.create(name='India')
        team2 = Team.objects.create(name='Australia')
        match = Match.objects.create(
            cricapi_id='m2',
            name='India vs Australia',
            team1=team1,
            team2=team2,
            format='odi',
            category='international',
            status='complete',
            match_date='2026-03-21',
        )

        mock_cricapi_get.return_value = {
            'status': 'success',
            'scorecard': [
                {
                    'inningsNumber': 1,
                    'batTeamName': 'India',
                    'score': 301,
                    'wickets': 6,
                    'overs': 50,
                    'runRate': 6.02,
                    'batting': [
                        {
                            'batsmanName': 'Virat Kohli',
                            'runs': 95,
                            'balls': 88,
                            'fours': 8,
                            'sixes': 1,
                            'strikeRate': 107.9,
                            'outDesc': 'c Smith b Starc',
                        }
                    ],
                    'bowling': [
                        {
                            'bowlerName': 'Mitchell Starc',
                            'overs': 10,
                            'runs': 58,
                            'wickets': 2,
                            'economy': 5.8,
                            'maidens': 1,
                        }
                    ],
                }
            ],
        }

        result = tasks.sync_player_stats.run(match_id='m2')

        self.assertEqual(result['synced'], 1)
        self.assertEqual(MatchScorecard.objects.filter(match=match).count(), 1)
        self.assertEqual(PlayerMatchStats.objects.filter(match=match).count(), 2)
        self.assertIsNotNone(cache.get('pipeline:player_stats:last_sync_at'))


class PipelineStatusEndpointTests(TestCase):
    def test_pipeline_status_endpoint_reads_cache(self):
        cache.set('pipeline:current_matches:last_sync_count', 12)
        cache.set('pipeline:current_matches:last_sync_at', '2026-03-19T10:00:00Z')

        client = APIClient()
        response = client.get('/api/v1/pipeline/status/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('pipeline', response.data)
        self.assertEqual(response.data['pipeline']['current_matches']['last_sync_count'], 12)
        self.assertEqual(response.data['pipeline']['current_matches']['last_sync_at'], '2026-03-19T10:00:00Z')
