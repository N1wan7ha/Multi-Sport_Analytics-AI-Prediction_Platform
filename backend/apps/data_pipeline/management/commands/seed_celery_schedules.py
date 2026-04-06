"""
Management command: seed_celery_schedules

Sets up the periodic Celery Beat schedules in the database.
Run once after first `migrate`.

Usage:
  python manage.py seed_celery_schedules
"""
from django.core.management.base import BaseCommand
from django.conf import settings
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

        # ── Every N minutes: auto-trigger live predictions ─
        every_live_prediction_minutes, _ = IntervalSchedule.objects.get_or_create(
            every=max(1, int(getattr(settings, 'LIVE_PREDICTION_SCHEDULE_MINUTES', 2))),
            period=IntervalSchedule.MINUTES,
        )
        PeriodicTask.objects.update_or_create(
            name='Auto Trigger Live Predictions',
            defaults={
                'task': 'apps.predictions.tasks.schedule_live_predictions',
                'interval': every_live_prediction_minutes,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write(
            f"  ✅ schedule_live_predictions — every {max(1, int(getattr(settings, 'LIVE_PREDICTION_SCHEDULE_MINUTES', 2)))} min"
        )

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

        # ── Every 6 hours: sync APILayer catalog (sports + affiliates) ─
        PeriodicTask.objects.update_or_create(
            name='Sync APILayer Catalog (6h)',
            defaults={
                'task': 'apps.data_pipeline.tasks.sync_apilayer_catalog',
                'interval': every_6h,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write('  ✅ sync_apilayer_catalog — every 6 hours')

        # ── Every 5 minutes: prediction-ready email notifications ─
        prediction_notify_5min, _ = IntervalSchedule.objects.get_or_create(
            every=5, period=IntervalSchedule.MINUTES
        )
        PeriodicTask.objects.update_or_create(
            name='Send Prediction Ready Notifications (5min)',
            defaults={
                'task': 'apps.accounts.tasks.send_prediction_ready_notifications',
                'interval': prediction_notify_5min,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write('  ✅ send_prediction_ready_notifications — every 5 min')

        # ── Every 10 minutes: match-start reminder emails ─
        match_start_10min, _ = IntervalSchedule.objects.get_or_create(
            every=10, period=IntervalSchedule.MINUTES
        )
        PeriodicTask.objects.update_or_create(
            name='Send Match Start Notifications (10min)',
            defaults={
                'task': 'apps.accounts.tasks.send_match_start_notifications',
                'interval': match_start_10min,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write('  ✅ send_match_start_notifications — every 10 min')

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

        # ── Daily at 00:20: generate data quality report ─────────
        quality_report_time, _ = CrontabSchedule.objects.get_or_create(
            minute='20',
            hour='0',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='Asia/Kolkata',
        )
        PeriodicTask.objects.update_or_create(
            name='Run Data Quality Report Pipeline (daily)',
            defaults={
                'task': 'apps.data_pipeline.tasks.run_data_quality_report_pipeline',
                'crontab': quality_report_time,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write('  ✅ run_data_quality_report_pipeline — daily at 00:20 IST')

        # ── Daily at 00:30: run rolling-window retraining ─
        rolling_retrain, _ = CrontabSchedule.objects.get_or_create(
            minute='30',
            hour='0',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='Asia/Kolkata',
        )
        PeriodicTask.objects.update_or_create(
            name='Run Rolling Window Model Retraining (daily)',
            defaults={
                'task': 'apps.data_pipeline.tasks.run_rolling_window_retraining_pipeline',
                'crontab': rolling_retrain,
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write('  ✅ run_rolling_window_retraining_pipeline — daily at 00:30 IST')

        self.stdout.write(self.style.SUCCESS('\n🎯 All Celery Beat schedules configured!'))
