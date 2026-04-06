"""Analytics app URLs."""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('team/<str:team_name>/', views.TeamAnalyticsView.as_view(), name='team'),
    path('player/<int:player_id>/', views.PlayerAnalyticsView.as_view(), name='player'),
    path('dashboard/', views.DashboardStatsView.as_view(), name='dashboard'),
    path('teams/international/', views.InternationalTeamsView.as_view(), name='international-teams'),
    path('players/top/', views.TopPlayersView.as_view(), name='top-players'),
    path('news/', views.CricketNewsView.as_view(), name='news'),
    path('standings/international/', views.InternationalStandingsView.as_view(), name='international-standings'),
]
