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
        # ── Every 5 minutes: sync live match data ───────────
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

        # ── Every 1 hour: sync completed match results ──────
        every_1h, _ = IntervalSchedule.objects.get_or_create(
            every=60, period=IntervalSchedule.MINUTES
        )
        PeriodicTask.objects.update_or_create(
            name='Sync Cricbuzz Completed Matches (1h)',
            defaults={
                'task': 'apps.data_pipeline.tasks.sync_completed_matches',
                'interval': every_1h,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write('  ✅ sync_completed_matches — every 1 hour')

        # ── Every 6 hours: sync player stats ────────────────
        every_6h, _ = IntervalSchedule.objects.get_or_create(
            every=360, period=IntervalSchedule.MINUTES
        )
        PeriodicTask.objects.update_or_create(
            name='Sync Player Stats (6h)',
            defaults={
                'task': 'apps.data_pipeline.tasks.sync_player_stats',
                'interval': every_6h,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write('  ✅ sync_player_stats — every 6 hours')

        # ── Daily at midnight: run model retraining ─────────
        midnight, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='0',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='Asia/Kolkata',
        )
        PeriodicTask.objects.update_or_create(
            name='Run Model Retraining Pipeline (daily)',
            defaults={
                'task': 'apps.data_pipeline.tasks.run_model_retraining_pipeline',
                'crontab': midnight,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write('  ✅ run_model_retraining_pipeline — daily at 00:00 IST')

        self.stdout.write(self.style.SUCCESS('\n🎯 All Celery Beat schedules configured!'))
