"""Matches app models."""
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=150, unique=True)
    short_name = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=100, blank=True)
    is_international = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'teams'
        ordering = ['name']

    def __str__(self):
        return self.name


class Venue(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    pitch_type = models.CharField(
        max_length=20,
        choices=[('batting', 'Batting'), ('bowling', 'Bowling'), ('balanced', 'Balanced')],
        default='balanced'
    )
    avg_first_innings_score = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'venues'

    def __str__(self):
        return f"{self.name}, {self.city}"


class Match(models.Model):
    FORMAT_CHOICES = [
        ('test', 'Test'),
        ('odi', 'ODI'),
        ('t20', 'T20'),
        ('t10', 'T10'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('live', 'Live'),
        ('complete', 'Complete'),
        ('abandoned', 'Abandoned'),
    ]
    CATEGORY_CHOICES = [
        ('international', 'International'),
        ('franchise', 'Franchise'),
        ('domestic', 'Domestic'),
    ]

    # Source tracking
    cricapi_id = models.CharField(max_length=100, blank=True, db_index=True)
    cricbuzz_id = models.CharField(max_length=100, blank=True, db_index=True)

    # Match info
    name = models.CharField(max_length=300)
    team1 = models.ForeignKey(Team, related_name='home_matches', on_delete=models.SET_NULL, null=True)
    team2 = models.ForeignKey(Team, related_name='away_matches', on_delete=models.SET_NULL, null=True)
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='t20')
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default='international')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='upcoming')

    # Schedule
    match_date = models.DateField(null=True, blank=True)
    match_datetime = models.DateTimeField(null=True, blank=True)

    # Result
    result_text = models.TextField(blank=True)
    winner = models.ForeignKey(Team, related_name='won_matches', on_delete=models.SET_NULL, null=True, blank=True)
    toss_winner = models.ForeignKey(Team, related_name='toss_wins', on_delete=models.SET_NULL, null=True, blank=True)
    toss_decision = models.CharField(max_length=10, blank=True)  # bat / field

    # Raw data snapshot (for debugging / ML training)
    raw_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'matches'
        ordering = ['-match_date']
        indexes = [
            models.Index(fields=['status', 'match_date']),
            models.Index(fields=['format', 'category']),
        ]

    def __str__(self):
        return f"{self.name} ({self.match_date})"


class MatchScorecard(models.Model):
    """Stores innings-level scorecard data."""
    match = models.ForeignKey(Match, related_name='scorecards', on_delete=models.CASCADE)
    innings_number = models.PositiveSmallIntegerField()  # 1 or 2
    batting_team = models.ForeignKey(Team, related_name='batting_innings', on_delete=models.SET_NULL, null=True)
    total_runs = models.IntegerField(default=0)
    total_wickets = models.IntegerField(default=0)
    total_overs = models.FloatField(default=0)
    run_rate = models.FloatField(default=0)
    batting_data = models.JSONField(default=list)   # list of {batsman, runs, balls, 4s, 6s, sr}
    bowling_data = models.JSONField(default=list)   # list of {bowler, overs, maidens, runs, wickets, economy}

    class Meta:
        db_table = 'match_scorecards'
        unique_together = ('match', 'innings_number')

    def __str__(self):
        return f"{self.match} - Innings {self.innings_number}"
