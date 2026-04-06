"""
Management command: sync_matches

Usage:
    python manage.py sync_matches              # sync current + live + completed + series
  python manage.py sync_matches --source=cricapi
  python manage.py sync_matches --source=cricbuzz
    python manage.py sync_matches --source=apilayer
    python manage.py sync_matches --source=completed
    python manage.py sync_matches --source=player_stats --match-id=<id>
"""
from django.core.management.base import BaseCommand, CommandError
from apps.data_pipeline.tasks import (
    sync_apilayer_catalog,
        sync_completed_matches,
        sync_cricbuzz_live,
        sync_current_matches,
        sync_player_stats,
    sync_rapidapi_players,
    sync_rapidapi_team_logos,
    sync_rapidapi_teams,
        sync_series,
        sync_unified_matches,
)


class Command(BaseCommand):
    help = 'Sync cricket match data from APIs to the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='all',
            choices=['all', 'cricapi', 'cricbuzz', 'completed', 'series', 'player_stats', 'unified', 'teams', 'players', 'team_logos', 'apilayer'],
            help='Which data source to sync (default: all)',
        )
        parser.add_argument(
            '--match-id',
            type=str,
            default='',
            help='Optional match id for player stats sync',
        )
        parser.add_argument(
            '--team-id',
            type=int,
            default=None,
            help='Optional team id for RapidAPI players sync',
        )

    def handle(self, *args, **options):
        source = options['source']
        match_id = options['match_id']
        team_id = options['team_id']
        is_all = source == 'all'
        failed_steps = []

        def run_step(step_name, title, action, success_message):
            self.stdout.write(title)
            try:
                result = action()
            except Exception as exc:
                failed_steps.append((step_name, str(exc)))
                self.stderr.write(self.style.WARNING(f"  [WARN] {step_name} failed: {exc}"))
                return None

            self.stdout.write(self.style.SUCCESS(success_message(result or {})))
            return result

        if source in ('all', 'cricapi'):
            run_step(
                'CricAPI current matches',
                '[SYNC] Syncing current matches from CricAPI...',
                sync_current_matches,
                lambda result: f"  [OK] CricAPI: {result.get('synced', 0)} matches synced",
            )

        if source in ('all', 'cricbuzz'):
            run_step(
                'Cricbuzz live matches',
                '[SYNC] Syncing live matches from Cricbuzz...',
                sync_cricbuzz_live,
                lambda result: f"  [OK] Cricbuzz: {result.get('synced', 0)} live matches synced",
            )

        if source in ('all', 'completed'):
            run_step(
                'Completed matches',
                '[SYNC] Syncing recently completed matches from Cricbuzz...',
                sync_completed_matches,
                lambda result: f"  [OK] Completed: {result.get('synced', 0)} matches synced",
            )

        if source in ('all', 'series'):
            run_step(
                'Series sync',
                '[SYNC] Syncing series from CricAPI...',
                sync_series,
                lambda result: f"  [OK] Series: {result.get('synced', 0)} series synced",
            )

        if source in ('all', 'player_stats'):
            if match_id:
                title = f'[SYNC] Syncing player stats for match {match_id}...'
            else:
                title = '[SYNC] Syncing player stats for recently completed matches...'
            run_step(
                'Player stats sync',
                title,
                lambda: sync_player_stats(match_id=match_id or None),
                lambda result: f"  [OK] Player stats: {result.get('synced', 0)} matches processed",
            )

        if source in ('all', 'teams'):
            run_step(
                'RapidAPI teams sync',
                '[SYNC] Syncing teams from RapidAPI...',
                sync_rapidapi_teams,
                lambda result: f"  [OK] Teams: {result.get('synced', 0)} teams synced",
            )

        if source in ('all', 'team_logos'):
            run_step(
                'RapidAPI team logos sync',
                '[SYNC] Syncing team logos from RapidAPI...',
                sync_rapidapi_team_logos,
                lambda result: f"  [OK] Team logos: {result.get('updated', 0)} teams updated",
            )

        if source in ('all', 'players'):
            if team_id is not None:
                title = f'[SYNC] Syncing players from RapidAPI for team id {team_id}...'
            else:
                title = '[SYNC] Syncing players from RapidAPI for top local teams...'
            run_step(
                'RapidAPI players sync',
                title,
                lambda: sync_rapidapi_players(team_id=team_id),
                lambda result: f"  [OK] Players: {result.get('synced', 0)} players synced",
            )

        if source in ('all', 'apilayer'):
            run_step(
                'APILayer catalog sync',
                '[SYNC] Syncing APILayer catalog (cricket-filtered)...',
                sync_apilayer_catalog,
                lambda result: (
                    f"  [OK] APILayer: sports={result.get('sports_total', 0)} "
                    f"cricket_filtered={result.get('sports_filtered', 0)} "
                    f"affiliates={result.get('affiliates_total', 0)} "
                    f"status={result.get('status', 'unknown')}"
                ),
            )

        if source == 'unified':
            run_step(
                'Unified sync',
                '[SYNC] Running unified sync (CricAPI + Cricbuzz dedupe)...',
                sync_unified_matches,
                lambda result: f"  [OK] Unified: {result.get('synced', 0)} merged matches synced",
            )

        if failed_steps:
            self.stderr.write(self.style.WARNING('\n[WARN] Some sync steps failed:'))
            for step_name, error in failed_steps:
                self.stderr.write(self.style.WARNING(f"  - {step_name}: {error}"))

            if not is_all:
                raise CommandError(f"Sync failed for source '{source}'. See warnings above.")

        self.stdout.write(self.style.SUCCESS('\nMatch sync complete!'))
