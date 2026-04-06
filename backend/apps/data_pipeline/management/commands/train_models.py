from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max

from apps.matches.models import Match
from ml_engine.training import train_models_for_year_range, train_models_from_matches
from ml_engine.walk_forward_trainer import train_walk_forward_models


class Command(BaseCommand):
    help = 'Train prediction models from stored match data using multiple training modes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            default='rolling',
            choices=['full', 'rolling', 'year-range', 'walk-forward'],
            help='Training strategy. full=all data, rolling=recent years, year-range=explicit years, walk-forward=time-series validation.',
        )
        parser.add_argument(
            '--model-version',
            type=str,
            default='',
            dest='model_version',
            help='Optional explicit model version label.',
        )
        parser.add_argument(
            '--years',
            type=int,
            default=0,
            help='Rolling mode only: recent N years to train on (default from ML_ROLLING_WINDOW_YEARS).',
        )
        parser.add_argument('--start-year', type=int, default=0, help='Year-range mode start year.')
        parser.add_argument('--end-year', type=int, default=0, help='Year-range mode end year.')

    def handle(self, *args, **options):
        mode = str(options.get('mode') or 'rolling').strip().lower()
        version_arg = str(options.get('model_version') or '').strip()

        if mode == 'full':
            version = version_arg or str(getattr(settings, 'ML_MODEL_VERSION', 'v1.0'))
            summary = train_models_from_matches(settings.ML_MODEL_PATH, version=version)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Training complete mode=full version={summary.version} samples={summary.sample_count} model={summary.model_type} accuracy={summary.accuracy} auc={summary.auc_roc} brier={summary.brier_score}"
                )
            )
            return

        if mode == 'rolling':
            years = int(options.get('years') or 0)
            if years <= 0:
                years = max(1, int(getattr(settings, 'ML_ROLLING_WINDOW_YEARS', 3)))

            latest_year = Match.objects.filter(
                status='complete',
                match_date__isnull=False,
            ).aggregate(max_year=Max('match_date__year')).get('max_year')

            if not latest_year:
                raise CommandError('No completed matches with match_date found for rolling training.')

            end_year = int(latest_year)
            start_year = int(end_year - years + 1)
            version = version_arg or f"{settings.ML_MODEL_VERSION}-rolling-{start_year}-{end_year}"

            summary = train_models_for_year_range(
                settings.ML_MODEL_PATH,
                version=version,
                start_year=start_year,
                end_year=end_year,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Training complete mode=rolling version={summary.version} years={start_year}-{end_year} samples={summary.sample_count} model={summary.model_type} accuracy={summary.accuracy} auc={summary.auc_roc} brier={summary.brier_score}"
                )
            )
            return

        if mode == 'year-range':
            start_year = int(options.get('start_year') or 0)
            end_year = int(options.get('end_year') or 0)
            if start_year <= 0 or end_year <= 0:
                raise CommandError('year-range mode requires --start-year and --end-year.')

            if start_year > end_year:
                start_year, end_year = end_year, start_year

            version = version_arg or f"{settings.ML_MODEL_VERSION}-range-{start_year}-{end_year}"
            summary = train_models_for_year_range(
                settings.ML_MODEL_PATH,
                version=version,
                start_year=start_year,
                end_year=end_year,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Training complete mode=year-range version={summary.version} years={start_year}-{end_year} samples={summary.sample_count} model={summary.model_type} accuracy={summary.accuracy} auc={summary.auc_roc} brier={summary.brier_score}"
                )
            )
            return

        version = version_arg or f"{settings.ML_MODEL_VERSION}-walk-forward"
        result = train_walk_forward_models(settings.ML_MODEL_PATH, version=version)
        if result.get('success'):
            avg_metrics = result.get('avg_metrics') or {}
            self.stdout.write(
                self.style.SUCCESS(
                    f"Training complete mode=walk-forward version={version} folds={result.get('num_folds')} avg_metrics={avg_metrics}"
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"Walk-forward training finished with warnings/errors: {result}"
            )
        )
