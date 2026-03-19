"""
Management command: sync_matches

Usage:
    python manage.py sync_matches              # sync current + live + completed + series
  python manage.py sync_matches --source=cricapi
  python manage.py sync_matches --source=cricbuzz
    python manage.py sync_matches --source=completed
    python manage.py sync_matches --source=player_stats --match-id=<id>
"""
from django.core.management.base import BaseCommand
from apps.data_pipeline.tasks import (
        sync_completed_matches,
        sync_cricbuzz_live,
        sync_current_matches,
        sync_player_stats,
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
            choices=['all', 'cricapi', 'cricbuzz', 'completed', 'series', 'player_stats', 'unified'],
            help='Which data source to sync (default: all)',
        )
        parser.add_argument(
            '--match-id',
            type=str,
            default='',
            help='Optional match id for player stats sync',
        )

    def handle(self, *args, **options):
        source = options['source']
        match_id = options['match_id']

        if source in ('all', 'cricapi'):
            self.stdout.write('🔄 Syncing current matches from CricAPI...')
            result = sync_current_matches()
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ CricAPI: {result.get('synced', 0)} matches synced")
            )

        if source in ('all', 'cricbuzz'):
            self.stdout.write('🔄 Syncing live matches from Cricbuzz...')
            result = sync_cricbuzz_live()
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ Cricbuzz: {result.get('synced', 0)} live matches synced")
            )

        if source in ('all', 'completed'):
            self.stdout.write('🔄 Syncing recently completed matches from Cricbuzz...')
            result = sync_completed_matches()
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ Completed: {result.get('synced', 0)} matches synced")
            )

        if source in ('all', 'series'):
            self.stdout.write('🔄 Syncing series from CricAPI...')
            result = sync_series()
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ Series: {result.get('synced', 0)} series synced")
            )

        if source in ('all', 'player_stats'):
            if match_id:
                self.stdout.write(f'🔄 Syncing player stats for match {match_id}...')
            else:
                self.stdout.write('🔄 Syncing player stats for recently completed matches...')
            result = sync_player_stats(match_id=match_id or None)
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ Player stats: {result.get('synced', 0)} matches processed")
            )

        if source == 'unified':
            self.stdout.write('🔄 Running unified sync (CricAPI + Cricbuzz dedupe)...')
            result = sync_unified_matches()
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ Unified: {result.get('synced', 0)} merged matches synced")
            )

        self.stdout.write(self.style.SUCCESS('\n🏏 Sync complete!'))
