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
from apps.players.models import Player, PlayerMatchStats
from ml_engine.training import TrainingSummary


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

    @patch('apps.data_pipeline.tasks._extract_live_rows_with_fallback')
    def test_sync_cricbuzz_live_writes_live_match_rows(self, mock_extract_live_rows):
        mock_extract_live_rows.return_value = (
            [
                normalize_cricbuzz_live_match(
                    {
                        'matchId': 'cbz1',
                        'team1': {'teamName': 'MI'},
                        'team2': {'teamName': 'CSK'},
                        'matchFormat': 'T20',
                        'startDate': '1773964800000',
                        'venueInfo': {'ground': 'Eden Gardens'},
                    }
                )
            ],
            'rapidapi_cricbuzz2',
            '/matches/v1/live',
        )

        result = tasks.sync_cricbuzz_live.run()

        self.assertEqual(result['synced'], 1)
        self.assertEqual(Match.objects.count(), 1)
        created = Match.objects.get(cricbuzz_id='cbz1')
        self.assertEqual(created.status, 'live')
        self.assertEqual(created.category, 'international')
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


class ModelRetrainingTaskTests(TestCase):
    @patch('apps.data_pipeline.tasks.train_models_from_matches')
    def test_run_model_retraining_pipeline_writes_cache(self, mock_train_models):
        mock_train_models.return_value = TrainingSummary(
            version='v1.0',
            sample_count=120,
            model_type='sklearn_ensemble',
            accuracy=0.87,
            auc_roc=0.91,
            brier_score=0.18,
        )

        result = tasks.run_model_retraining_pipeline.run()

        self.assertEqual(result['version'], 'v1.0')
        self.assertEqual(result['sample_count'], 120)
        self.assertEqual(result['model_type'], 'sklearn_ensemble')
        self.assertEqual(cache.get('pipeline:model_retraining:last_result')['accuracy'], 0.87)
        self.assertIsNotNone(cache.get('pipeline:model_retraining:last_run_at'))

    def test_run_rolling_window_retraining_pipeline_skips_without_complete_matches(self):
        # Ensure the skip path is evaluated even when fixture/seed data exists.
        Match.objects.filter(status='complete').delete()
        result = tasks.run_rolling_window_retraining_pipeline.run()

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'no complete matches with match_date found')
        self.assertIsNotNone(cache.get('pipeline:model_retraining:rolling:last_run_at'))

    @patch('apps.data_pipeline.tasks.train_models_for_year_range')
    def test_run_rolling_window_retraining_pipeline_calls_year_range_trainer(self, mock_train):
        team1, _ = Team.objects.get_or_create(name='India')
        team2, _ = Team.objects.get_or_create(name='England')
        Match.objects.create(
            name='India vs England Complete',
            team1=team1,
            team2=team2,
            status='complete',
            format='odi',
            category='international',
            match_date='2026-01-05',
        )

        mock_train.return_value = TrainingSummary(
            version='v1.0-rolling-2024-2026',
            sample_count=250,
            model_type='sklearn_ensemble',
            accuracy=0.8,
            auc_roc=0.86,
            brier_score=0.19,
        )

        result = tasks.run_rolling_window_retraining_pipeline.run(years=3)

        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['window_years'], 3)
        self.assertIsNotNone(result.get('end_year'))
        self.assertIsNotNone(result.get('start_year'))

        mock_train.assert_called_once()
        call_args = mock_train.call_args
        self.assertEqual(call_args.args[0], tasks.settings.ML_MODEL_PATH)
        self.assertEqual(call_args.kwargs['version'], result['version'])
        self.assertEqual(call_args.kwargs['start_year'], result['start_year'])
        self.assertEqual(call_args.kwargs['end_year'], result['end_year'])
        self.assertEqual(cache.get('pipeline:model_retraining:rolling:last_result')['version'], 'v1.0-rolling-2024-2026')


class RapidApiCatalogSyncTests(TestCase):
    @patch('apps.data_pipeline.tasks._rapidapi_get_with_fallback')
    def test_sync_rapidapi_teams_creates_team_rows(self, mock_rapidapi_get):
        mock_rapidapi_get.side_effect = [
            ({'data': [{'name': 'India', 'shortName': 'IND', 'country': 'India'}]}, 'rapidapi_free', '/cricket-teams'),
            ({'data': [{'name': 'Australia Women', 'shortName': 'AUSW', 'country': 'Australia'}]}, 'rapidapi_free', '/cricket-teams-women'),
            ({'data': [{'name': 'Chennai Super Kings', 'shortName': 'CSK', 'country': 'India'}]}, 'rapidapi_free', '/cricket-teams-ipl'),
            ({'data': [{'name': 'Mumbai', 'shortName': 'MUM', 'country': 'India'}]}, 'rapidapi_free', '/cricket-teams-bbl'),
            ({'data': [{'name': 'India', 'logo': 'https://img.example.com/india.png'}]}, 'rapidapi_free', '/cricket-team-logo'),
        ]

        result = tasks.sync_rapidapi_teams.run()

        self.assertEqual(result['synced'], 4)
        self.assertEqual(result['logos_updated'], 1)
        self.assertTrue(Team.objects.filter(name='India').exists())
        self.assertTrue(Team.objects.filter(name='Chennai Super Kings').exists())
        self.assertEqual(Team.objects.get(name='India').logo_url, 'https://img.example.com/india.png')

    @patch('apps.data_pipeline.tasks._rapidapi_get_with_fallback')
    def test_sync_rapidapi_players_creates_player_rows(self, mock_rapidapi_get):
        team = Team.objects.create(name='India')
        mock_rapidapi_get.return_value = (
            {
                'data': [
                    {
                        'id': 'p-1',
                        'name': 'Virat Kohli',
                        'fullName': 'Virat Kohli',
                        'country': 'India',
                        'role': 'batter',
                        'battingStyle': 'Right-hand bat',
                    }
                ]
            },
            'rapidapi_free',
            '/cricket-players?team=India',
        )

        result = tasks.sync_rapidapi_players.run(team_id=team.id)

        self.assertEqual(result['synced'], 1)
        player = Player.objects.get(name='Virat Kohli')
        self.assertEqual(player.cricapi_id, 'p-1')
        self.assertEqual(player.role, 'batsman')

    @patch('apps.data_pipeline.tasks._rapidapi_get_with_fallback')
    def test_sync_rapidapi_team_logos_updates_existing_team(self, mock_rapidapi_get):
        Team.objects.create(name='India')
        mock_rapidapi_get.return_value = (
            {
                'data': [
                    {
                        'name': 'India',
                        'logo': 'https://img.example.com/india-logo.png',
                    }
                ]
            },
            'rapidapi_free',
            '/cricket-team-logo',
        )

        result = tasks.sync_rapidapi_team_logos.run()

        self.assertEqual(result['updated'], 1)
        self.assertEqual(Team.objects.get(name='India').logo_url, 'https://img.example.com/india-logo.png')
