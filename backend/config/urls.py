"""Root URL Configuration — MatchMind (Multi-Sport Prediction Platform)."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from apps.accounts.views import CustomTokenObtainPairView
from apps.core.views import HealthView, ReadyView

API_PREFIX = 'api/v1/'

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Prometheus metrics
    path('', include('django_prometheus.urls')),

    # ── JWT Auth ───────────────────────────
    path(f'{API_PREFIX}auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path(f'{API_PREFIX}auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path(f'{API_PREFIX}auth/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # ── Service Health ─────────────────────
    path(f'{API_PREFIX}health/', HealthView.as_view(), name='health'),
    path(f'{API_PREFIX}ready/', ReadyView.as_view(), name='ready'),

    # ── App Routers ────────────────────────
    path(f'{API_PREFIX}auth/', include('apps.accounts.urls')),    path(f'{API_PREFIX}admin/', include('apps.admin_api.urls')),    path(f'{API_PREFIX}matches/', include('apps.matches.urls')),
    path(f'{API_PREFIX}players/', include('apps.players.urls')),
    path(f'{API_PREFIX}series/', include('apps.series.urls')),
    path(f'{API_PREFIX}predictions/', include('apps.predictions.urls')),
    path(f'{API_PREFIX}analytics/', include('apps.analytics.urls')),
    path(f'{API_PREFIX}pipeline/', include('apps.data_pipeline.urls')),
]

# Serve media in dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
