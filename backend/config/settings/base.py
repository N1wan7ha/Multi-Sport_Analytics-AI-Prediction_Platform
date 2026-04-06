"""
Django Base Settings — MatchMind (Multi-Sport Prediction Platform)
"""
import os
from pathlib import Path
from decouple import config
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─── Security ─────────────────────────────────────────────
SECRET_KEY = config('DJANGO_SECRET_KEY', default='change-me-in-production')
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost').split(',')

# ─── Applications ─────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'daphne',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'channels',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'django_celery_beat',
    'django_celery_results',
    'django_prometheus',
]

LOCAL_APPS = [
    'apps.core',
    'apps.accounts',
    'apps.matches',
    'apps.players',
    'apps.series',
    'apps.predictions',
    'apps.analytics',
    'apps.data_pipeline',
    'apps.data_quality',
    'apps.admin_api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ────────────────────────────────────────────
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'apps.core.middleware.SecurityHeadersMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ─── Database ─────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='matchmind_db'),
        'USER': config('DB_USER', default='matchmind_user'),
        'PASSWORD': config('DB_PASSWORD', default='matchmind_pwd'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# ─── Cache (Redis) ────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 300,  # 5 min default TTL
    }
}

# ─── Auth ─────────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'
SITE_ID = config('SITE_ID', default=1, cast=int)

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_UNIQUE_EMAIL = True

GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:4200')
EMAIL_VERIFICATION_TOKEN_MAX_AGE = config('EMAIL_VERIFICATION_TOKEN_MAX_AGE', default=86400, cast=int)

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': GOOGLE_CLIENT_ID,
            'secret': GOOGLE_CLIENT_SECRET,
            'key': '',
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── DRF + JWT ────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/min',
        'user': '1000/min',
    },
    # Keep `format` available for domain filters like cricket match format (odi/t20).
    'URL_FORMAT_OVERRIDE': None,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=config('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=60, cast=int)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=config('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'TOKEN_OBTAIN_SERIALIZER': 'apps.accounts.serializers.CustomTokenObtainPairSerializer',
}

# ─── CORS ─────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'http://localhost:4200',
    'http://127.0.0.1:4200',
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = config(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    default='http://localhost:4200,http://127.0.0.1:4200'
).split(',')

SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_RESOURCE_POLICY = 'same-origin'

# ─── Celery ───────────────────────────────────────────────
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/2')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 min max task runtime

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL', default='redis://localhost:6379/0')],
        },
    },
}

# ─── External APIs ────────────────────────────────────────
CRICAPI_KEY = config('CRICAPI_KEY', default='')
CRICAPI_BASE_URL = config('CRICAPI_BASE_URL', default='https://api.cricapi.com/v1')

CRICBUZZ_RAPIDAPI_KEY = config('CRICBUZZ_RAPIDAPI_KEY', default='')
CRICBUZZ_RAPIDAPI_HOST = config('CRICBUZZ_RAPIDAPI_HOST', default='cricket-api-free-data.p.rapidapi.com')
CRICBUZZ_BASE_URL = config('CRICBUZZ_BASE_URL', default='https://cricket-api-free-data.p.rapidapi.com')

# RapidAPI free-data host for `/cricket-*` catalog endpoints.
RAPIDAPI_FREE_KEY = config('RAPIDAPI_FREE_KEY', default=CRICBUZZ_RAPIDAPI_KEY)
RAPIDAPI_FREE_HOST = config('RAPIDAPI_FREE_HOST', default='cricket-api-free-data.p.rapidapi.com')
RAPIDAPI_FREE_BASE_URL = config('RAPIDAPI_FREE_BASE_URL', default='https://cricket-api-free-data.p.rapidapi.com')

# livescore6 host for `/matches/v2/*` cricket endpoints.
LIVESCORE6_RAPIDAPI_KEY = config('LIVESCORE6_RAPIDAPI_KEY', default=CRICBUZZ_RAPIDAPI_KEY)
LIVESCORE6_RAPIDAPI_HOST = config('LIVESCORE6_RAPIDAPI_HOST', default='livescore6.p.rapidapi.com')
LIVESCORE6_BASE_URL = config('LIVESCORE6_BASE_URL', default='https://livescore6.p.rapidapi.com')

# Alternative Super Sources
CRICKET_LIVESCORE_HOST = config('CRICKET_LIVESCORE_HOST', default='cricket-livescore.p.rapidapi.com')
CRICKET_LIVESCORE_URL = config('CRICKET_LIVESCORE_URL', default='https://cricket-livescore.p.rapidapi.com')

LIVE_SCORE_CRICKET_HOST = config('LIVE_SCORE_CRICKET_HOST', default='live-score-cricket.p.rapidapi.com')
LIVE_SCORE_CRICKET_URL = config('LIVE_SCORE_CRICKET_URL', default='https://live-score-cricket.p.rapidapi.com')

# APILayer odds/therundown (current usage is cricket-filtered catalog sync).
APILAYER_API_KEY = config('APILAYER_API_KEY', default='')
APILAYER_ODDS_BASE_URL = config('APILAYER_ODDS_BASE_URL', default='https://api.apilayer.com/odds')
APILAYER_THERUNDOWN_BASE_URL = config('APILAYER_THERUNDOWN_BASE_URL', default='https://api.apilayer.com/therundown')
APILAYER_PRIMARY_SPORT = config('APILAYER_PRIMARY_SPORT', default='cricket')

# ─── ML Engine ────────────────────────────────────────────
ML_MODEL_PATH = config('ML_MODEL_PATH', default=str(BASE_DIR / 'ml_engine' / 'artifacts'))
ML_MODEL_VERSION = config('ML_MODEL_VERSION', default='v1.0')
ML_AUTO_SELECT_BEST_MODEL = config('ML_AUTO_SELECT_BEST_MODEL', default=True, cast=bool)
ML_ROLLING_WINDOW_YEARS = config('ML_ROLLING_WINDOW_YEARS', default=3, cast=int)

# Optional vector-context augmentation (Weaviate-backed).
ML_VECTOR_CONTEXT_ENABLED = config('ML_VECTOR_CONTEXT_ENABLED', default=False, cast=bool)
ML_VECTOR_TOP_K = config('ML_VECTOR_TOP_K', default=6, cast=int)
ML_VECTOR_MAX_PROB_SHIFT = config('ML_VECTOR_MAX_PROB_SHIFT', default=0.06, cast=float)

WEAVIATE_URL = config('WEAVIATE_URL', default='http://localhost:8080')
WEAVIATE_API_KEY = config('WEAVIATE_API_KEY', default='')
WEAVIATE_CLASS_NAME = config('WEAVIATE_CLASS_NAME', default='MatchContext')
WEAVIATE_TIMEOUT_SECONDS = config('WEAVIATE_TIMEOUT_SECONDS', default=3.0, cast=float)

LIVE_PREDICTION_OVER_STEP = config('LIVE_PREDICTION_OVER_STEP', default=2, cast=int)
LIVE_PREDICTION_SCHEDULE_MINUTES = config('LIVE_PREDICTION_SCHEDULE_MINUTES', default=2, cast=int)
MATCH_START_NOTIFICATION_WINDOW_MINUTES = config('MATCH_START_NOTIFICATION_WINDOW_MINUTES', default=30, cast=int)

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@matchmind.dev')

# ─── Internationalisation ─────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ─── Static / Media ───────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Logging ──────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'apps': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        'celery': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
