"""Predictions app URLs."""
from django.urls import path
from . import views

app_name = 'predictions'

urlpatterns = [
    path('', views.PredictionCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PredictionDetailView.as_view(), name='detail'),
    path('match/<int:match_id>/', views.MatchLatestPredictionView.as_view(), name='match-latest'),
]
