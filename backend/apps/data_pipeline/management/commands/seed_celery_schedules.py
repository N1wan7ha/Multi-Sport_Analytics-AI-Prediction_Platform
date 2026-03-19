"""
Management command: seed_celery_schedules

Sets up the periodic Celery Beat schedules in the database.
Run once after first `migrate`.

Usage:
  python manage.py seed_celery_schedules
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Seed Celery Beat periodic task schedules'

    def handle(self, *args, **options):
        # ── Every 5 minutes: sync live matches ──────────────
        every_5min, _ = IntervalSchedule.objects.get_or_create(
            every=5, period=IntervalSchedule.MINUTES
        )
        PeriodicTask.objects.update_or_create(
            name='Sync Cricbuzz Live Matches (5min)',
            defaults={
                'task': 'apps.data_pipeline.tasks.sync_cricbuzz_live',
                'interval': every_5min,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write('  ✅ sync_cricbuzz_live — every 5 min')

        # ── Every 30 minutes: sync CricAPI current matches ──
        every_30min, _ = IntervalSchedule.objects.get_or_create(
            every=30, period=IntervalSchedule.MINUTES
        )
        PeriodicTask.objects.update_or_create(
            name='Sync CricAPI Current Matches (30min)',
            defaults={
                'task': 'apps.data_pipeline.tasks.sync_current_matches',
                'interval': every_30min,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write('  ✅ sync_current_matches — every 30 min')

        # ── Every 6 hours: sync series ───────────────────────
        every_6h, _ = IntervalSchedule.objects.get_or_create(
            every=360, period=IntervalSchedule.MINUTES
        )
        PeriodicTask.objects.update_or_create(
            name='Sync CricAPI Series (6h)',
            defaults={
                'task': 'apps.data_pipeline.tasks.sync_series',
                'interval': every_6h,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write('  ✅ sync_series — every 6 hours')

        self.stdout.write(self.style.SUCCESS('\n🎯 All Celery Beat schedules configured!'))
