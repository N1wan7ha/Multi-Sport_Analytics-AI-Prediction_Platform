"""Quick dev settings that keep PostgreSQL defaults and simplify local development."""
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True

# Disable REST throttling in dev
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []

# Disable Redis cache in local dev (use in-memory)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# Disable Celery in local dev (tasks run synchronously)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Route emails to console during development.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Keep ML artifacts local in non-Docker dev sessions.
ML_MODEL_PATH = str(BASE_DIR / 'ml_engine' / 'artifacts')
