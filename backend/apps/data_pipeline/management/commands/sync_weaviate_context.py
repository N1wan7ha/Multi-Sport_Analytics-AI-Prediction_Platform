from __future__ import annotations

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ml_engine.vector_db_integration import index_completed_matches_to_weaviate


HTTP_LOGGER_NAMES = (
    'httpx',
    'httpcore',
)


class Command(BaseCommand):
    help = 'Index completed matches into Weaviate for vector-context retrieval.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Maximum number of completed matches to index (0 = no limit).',
        )
        parser.add_argument(
            '--since-days',
            type=int,
            default=0,
            help='Only index matches from the last N days (0 = all historical).',
        )
        parser.add_argument(
            '--verbose-http',
            action='store_true',
            help='Show HTTP client request logs during sync.',
        )

    def handle(self, *args, **options):
        limit = int(options.get('limit') or 0)
        since_days = int(options.get('since_days') or 0)
        verbose_http = bool(options.get('verbose_http'))

        since_date = None
        if since_days > 0:
            since_date = (timezone.now() - timedelta(days=since_days)).date()

        logger_levels: list[tuple[logging.Logger, int]] = []
        if not verbose_http:
            for logger_name in HTTP_LOGGER_NAMES:
                logger_obj = logging.getLogger(logger_name)
                logger_levels.append((logger_obj, logger_obj.level))
                logger_obj.setLevel(logging.WARNING)

        try:
            summary = index_completed_matches_to_weaviate(limit=limit, since_date=since_date)
        finally:
            for logger_obj, level in logger_levels:
                logger_obj.setLevel(level)

        status = str(summary.get('status', 'unknown'))

        if status == 'ok':
            self.stdout.write(
                self.style.SUCCESS(
                    f"Weaviate sync complete: indexed={summary.get('indexed', 0)} failed={summary.get('failed', 0)}"
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"Weaviate sync status={status} reason={summary.get('reason', '')}"
            )
        )
