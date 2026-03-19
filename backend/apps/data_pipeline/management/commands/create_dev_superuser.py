"""
Management command: create_dev_superuser

Creates a default superuser for local development.
Safe to run multiple times (idempotent).

Usage:
  python manage.py create_dev_superuser
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

DEV_EMAIL    = 'admin@cricket.dev'
DEV_USERNAME = 'admin'
DEV_PASSWORD = 'admin1234'


class Command(BaseCommand):
    help = 'Create a default superuser for local development (idempotent)'

    def handle(self, *args, **options):
        if User.objects.filter(email=DEV_EMAIL).exists():
            self.stdout.write(self.style.WARNING(
                f'Superuser already exists → {DEV_EMAIL} / {DEV_PASSWORD}'
            ))
            return

        User.objects.create_superuser(
            username=DEV_USERNAME,
            email=DEV_EMAIL,
            password=DEV_PASSWORD,
            favourite_team='India'
        )
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Dev superuser created!\n'
            f'   Email   : {DEV_EMAIL}\n'
            f'   Password: {DEV_PASSWORD}\n'
            f'   Admin   : http://127.0.0.1:8000/admin/\n'
        ))
