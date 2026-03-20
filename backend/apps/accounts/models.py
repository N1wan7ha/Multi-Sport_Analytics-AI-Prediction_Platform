"""Custom User model."""
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.matches.models import Team


class User(AbstractUser):
    """Extended user with profile fields."""
    ROLE_ADMIN = 'ADMIN'
    ROLE_USER = 'USER'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_USER, 'User'),
    ]

    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_USER)
    bio = models.TextField(blank=True)
    favourite_team = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email


class UserFavouriteTeam(models.Model):
    user = models.ForeignKey(User, related_name='favourite_teams', on_delete=models.CASCADE)
    team = models.ForeignKey(Team, related_name='favoured_by_users', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_favourite_teams'
        unique_together = ('user', 'team')

    def __str__(self):
        return f"{self.user.email} -> {self.team.name}"


class NotificationDispatch(models.Model):
    TYPE_CHOICES = [
        ('match_start', 'Match Start'),
        ('prediction_ready', 'Prediction Ready'),
    ]

    user = models.ForeignKey(User, related_name='notification_dispatches', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    match = models.ForeignKey('matches.Match', null=True, blank=True, on_delete=models.CASCADE)
    prediction_job = models.ForeignKey('predictions.PredictionJob', null=True, blank=True, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification_dispatches'
        indexes = [models.Index(fields=['notification_type', 'sent_at'])]

    def __str__(self):
        return f"{self.user.email} [{self.notification_type}]"
