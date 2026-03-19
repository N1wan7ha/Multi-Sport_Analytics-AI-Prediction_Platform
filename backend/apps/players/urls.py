"""Players app URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.PlayerViewSet, basename='player')

app_name = 'players'

urlpatterns = [
    path('', include(router.urls)),
]
