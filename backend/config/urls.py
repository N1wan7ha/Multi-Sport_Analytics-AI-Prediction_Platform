"""Root URL Configuration — Cricket Analytics Platform."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

API_PREFIX = 'api/v1/'

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Prometheus metrics
    path('', include('django_prometheus.urls')),

    # ── JWT Auth ───────────────────────────
    path(f'{API_PREFIX}auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path(f'{API_PREFIX}auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path(f'{API_PREFIX}auth/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # ── App Routers ────────────────────────
    path(f'{API_PREFIX}auth/', include('apps.accounts.urls')),
    path(f'{API_PREFIX}matches/', include('apps.matches.urls')),
    path(f'{API_PREFIX}players/', include('apps.players.urls')),
    path(f'{API_PREFIX}series/', include('apps.series.urls')),
    path(f'{API_PREFIX}predictions/', include('apps.predictions.urls')),
    path(f'{API_PREFIX}analytics/', include('apps.analytics.urls')),
]

# Serve media in dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
