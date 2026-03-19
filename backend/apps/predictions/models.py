"""Predictions app models."""
from django.db import models
from django.conf import settings
from apps.matches.models import Match, Team


class PredictionJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('complete', 'Complete'),
        ('failed', 'Failed'),
    ]
    TYPE_CHOICES = [
        ('pre_match', 'Pre-Match'),
        ('live', 'Live In-Match'),
    ]

    match = models.ForeignKey(Match, related_name='prediction_jobs', on_delete=models.CASCADE)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    prediction_type = models.CharField(max_length=15, choices=TYPE_CHOICES, default='pre_match')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    celery_task_id = models.CharField(max_length=200, blank=True)
    model_version = models.CharField(max_length=20, default='v1.0')
    error_message = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'prediction_jobs'
        ordering = ['-requested_at']

    def __str__(self):
        return f"Prediction #{self.pk} for {self.match}"


class PredictionResult(models.Model):
    """Stores the output of a prediction job."""
    job = models.OneToOneField(PredictionJob, related_name='result', on_delete=models.CASCADE)
    team1 = models.ForeignKey(Team, related_name='team1_predictions', on_delete=models.SET_NULL, null=True)
    team2 = models.ForeignKey(Team, related_name='team2_predictions', on_delete=models.SET_NULL, null=True)

    # Prediction outputs
    team1_win_probability = models.FloatField()   # 0.0 to 1.0
    team2_win_probability = models.FloatField()   # 0.0 to 1.0
    draw_probability = models.FloatField(default=0.0)
    confidence_score = models.FloatField()         # 0.0 to 1.0

    # Explanation
    key_factors = models.JSONField(default=list)   # [{factor, impact, direction}]
    feature_snapshot = models.JSONField(default=dict)  # raw feature values used

    # Live-only fields
    current_over = models.IntegerField(null=True, blank=True)
    current_score = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prediction_results'

    def __str__(self):
        return f"Result for Job #{self.job_id}: {self.team1_win_probability:.0%} vs {self.team2_win_probability:.0%}"
