"""Management command to sync player match stats from scorecards."""
from django.core.management.base import BaseCommand

from apps.data_pipeline.tasks import sync_player_stats


class Command(BaseCommand):
    help = 'Sync player stats for one match or recent completed matches'

    def add_arguments(self, parser):
        parser.add_argument(
            '--match-id',
            type=str,
            default='',
            help='Optional CricAPI match id to sync scorecard stats for one match',
        )

    def handle(self, *args, **options):
        match_id = options['match_id']
        if match_id:
            self.stdout.write(f'Syncing player stats for match {match_id}...')
        else:
            self.stdout.write('Syncing player stats for recently completed matches...')

        result = sync_player_stats(match_id=match_id or None)
        self.stdout.write(self.style.SUCCESS(f"Processed {result.get('synced', 0)} matches"))
