"""Quick dev settings that use SQLite so we can check migrations without PostgreSQL running."""
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True

# SQLite for local dev without Docker
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'ATOMIC_REQUESTS': False,
    }
}

# Disable REST throttling in dev
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []

# Disable Redis cache in local dev (use in-memory)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable Celery in local dev (tasks run synchronously)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
