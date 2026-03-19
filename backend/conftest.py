"""
conftest.py — pytest configuration for the Django backend.
"""
import django
import pytest
from django.conf import settings


@pytest.fixture(scope='session')
def django_db_setup():
    """Use test database."""
    pass


def pytest_configure():
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # In-memory DB for fast tests
        'ATOMIC_REQUESTS': False,
    }
