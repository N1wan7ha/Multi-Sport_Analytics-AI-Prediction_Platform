"""
Management command: sync_matches

Usage:
  python manage.py sync_matches              # sync current + live
  python manage.py sync_matches --source=cricapi
  python manage.py sync_matches --source=cricbuzz
"""
from django.core.management.base import BaseCommand
from apps.data_pipeline.tasks import sync_current_matches, sync_cricbuzz_live, sync_series


class Command(BaseCommand):
    help = 'Sync cricket match data from APIs to the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='all',
            choices=['all', 'cricapi', 'cricbuzz', 'series'],
            help='Which data source to sync (default: all)',
        )

    def handle(self, *args, **options):
        source = options['source']

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

        if source in ('all', 'series'):
            self.stdout.write('🔄 Syncing series from CricAPI...')
            result = sync_series()
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ Series: {result.get('synced', 0)} series synced")
            )

        self.stdout.write(self.style.SUCCESS('\n🏏 Sync complete!'))
