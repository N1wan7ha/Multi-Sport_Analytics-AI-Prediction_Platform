"""Management command to sync series data from CricAPI."""
from django.core.management.base import BaseCommand

from apps.data_pipeline.tasks import sync_series


class Command(BaseCommand):
    help = 'Sync cricket series data from CricAPI'

    def handle(self, *args, **options):
        self.stdout.write('Syncing series from CricAPI...')
        result = sync_series()
        self.stdout.write(self.style.SUCCESS(f"Synced {result.get('synced', 0)} series"))
