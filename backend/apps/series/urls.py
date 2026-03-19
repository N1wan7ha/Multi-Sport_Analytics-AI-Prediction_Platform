"""Series app URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.SeriesViewSet, basename='series')

app_name = 'series'

urlpatterns = [
    path('', include(router.urls)),
]
