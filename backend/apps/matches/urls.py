"""Matches app URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.MatchViewSet, basename='match')

app_name = 'matches'

urlpatterns = [
    path('live/', views.LiveMatchesView.as_view(), name='live-matches'),
    path('', include(router.urls)),
]
