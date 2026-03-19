"""Management command to sync active/current matches from CricAPI."""
from django.core.management.base import BaseCommand

from apps.data_pipeline.tasks import sync_current_matches


class Command(BaseCommand):
    help = 'Sync current matches from CricAPI'

    def handle(self, *args, **options):
        self.stdout.write('Syncing current matches from CricAPI...')
        result = sync_current_matches()
        self.stdout.write(self.style.SUCCESS(f"Synced {result.get('synced', 0)} current matches"))
