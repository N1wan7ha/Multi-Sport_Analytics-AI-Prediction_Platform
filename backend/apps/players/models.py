"""Players app models."""
from django.db import models
from apps.matches.models import Team


class Player(models.Model):
    ROLE_CHOICES = [
        ('batsman', 'Batsman'),
        ('bowler', 'Bowler'),
        ('all_rounder', 'All-Rounder'),
        ('wicket_keeper', 'Wicket Keeper'),
    ]

    cricapi_id = models.CharField(max_length=100, blank=True, db_index=True)
    name = models.CharField(max_length=200)
    full_name = models.CharField(max_length=300, blank=True)
    country = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    batting_style = models.CharField(max_length=50, blank=True)
    bowling_style = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    image_url = models.URLField(blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    
    # Source tracking (Silver layer)
    primary_source = models.CharField(
        max_length=20,
        default='rapidapi_free',
        help_text='Primary API source for this player'
    )
    confidence_score = models.IntegerField(
        default=50,
        help_text='0-100: Confidence in accuracy'
    )
    source_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of 'provider': 'source_timestamp' pairs that contributed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'players'
        ordering = ['name']
        indexes = [
            models.Index(fields=['primary_source']),
            models.Index(fields=['confidence_score']),
        ]

    def __str__(self):
        return self.name


class PlayerMatchStats(models.Model):
    """Per-match player performance — used for ML feature engineering."""
    player = models.ForeignKey(Player, related_name='match_stats', on_delete=models.CASCADE)
    match = models.ForeignKey('matches.Match', on_delete=models.CASCADE)
    innings_number = models.PositiveSmallIntegerField(default=1)

    # Batting
    runs_scored = models.IntegerField(null=True, blank=True)
    balls_faced = models.IntegerField(null=True, blank=True)
    fours = models.IntegerField(default=0)
    sixes = models.IntegerField(default=0)
    strike_rate = models.FloatField(null=True, blank=True)
    dismissed = models.BooleanField(default=True)

    # Bowling
    overs_bowled = models.FloatField(null=True, blank=True)
    runs_conceded = models.IntegerField(null=True, blank=True)
    wickets_taken = models.IntegerField(null=True, blank=True)
    economy = models.FloatField(null=True, blank=True)
    maidens = models.IntegerField(default=0)

    class Meta:
        db_table = 'player_match_stats'
        unique_together = ('player', 'match', 'innings_number')
