"""Series app models."""
from django.db import models


class Series(models.Model):
    cricapi_id = models.CharField(max_length=100, blank=True, db_index=True)
    name = models.CharField(max_length=300)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    odi_matches_count = models.IntegerField(default=0)
    t20_matches_count = models.IntegerField(default=0)
    test_matches_count = models.IntegerField(default=0)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'series'
        ordering = ['-start_date']

    def __str__(self):
        return self.name
