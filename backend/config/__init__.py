"""config/__init__.py — ensure Celery app is loaded with Django."""
from .celery import app as celery_app

__all__ = ('celery_app',)
