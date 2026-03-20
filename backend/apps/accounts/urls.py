"""Accounts app URLs."""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('google/', views.GoogleAuthView.as_view(), name='google-auth'),
    path('verify-email/', views.ResendEmailVerificationView.as_view(), name='verify-email'),
    path('verify-email/confirm/', views.ConfirmEmailVerificationView.as_view(), name='verify-email-confirm'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('team-options/', views.TeamOptionsView.as_view(), name='team-options'),
    path('prediction-history/', views.PredictionHistoryView.as_view(), name='prediction-history'),
]
