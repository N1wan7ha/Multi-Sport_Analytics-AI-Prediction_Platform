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

DEV_EMAIL    = 'admin@matchmind.dev'
DEV_USERNAME = 'admin'
DEV_PASSWORD = 'admin1234'

DEV_USER_EMAIL = 'user@matchmind.dev'
DEV_USER_USERNAME = 'user'
DEV_USER_PASSWORD = 'user1234'


class Command(BaseCommand):
    help = 'Create a default superuser for local development (idempotent)'

    def handle(self, *args, **options):
        created_any = False

        if User.objects.filter(email=DEV_EMAIL).exists():
            self.stdout.write(self.style.WARNING(
                f'Superuser already exists → {DEV_EMAIL} / {DEV_PASSWORD}'
            ))
        else:
            User.objects.create_superuser(
                username=DEV_USERNAME,
                email=DEV_EMAIL,
                password=DEV_PASSWORD,
                favourite_team='India'
            )
            created_any = True
            self.stdout.write(self.style.SUCCESS(
                f'✅ Dev superuser created → {DEV_EMAIL} / {DEV_PASSWORD}'
            ))

        if User.objects.filter(email=DEV_USER_EMAIL).exists():
            self.stdout.write(self.style.WARNING(
                f'Dev user already exists → {DEV_USER_EMAIL} / {DEV_USER_PASSWORD}'
            ))
        else:
            User.objects.create_user(
                username=DEV_USER_USERNAME,
                email=DEV_USER_EMAIL,
                password=DEV_USER_PASSWORD,
                favourite_team='India',
                email_verified=True,
            )
            created_any = True
            self.stdout.write(self.style.SUCCESS(
                f'✅ Dev user created → {DEV_USER_EMAIL} / {DEV_USER_PASSWORD}'
            ))

        if created_any:
            self.stdout.write(self.style.SUCCESS(
                f'\nAdmin login : {DEV_EMAIL} / {DEV_PASSWORD}\n'
                f'User login  : {DEV_USER_EMAIL} / {DEV_USER_PASSWORD}\n'
            ))
