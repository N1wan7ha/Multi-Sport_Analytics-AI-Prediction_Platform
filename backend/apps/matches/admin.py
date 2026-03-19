"""Matches admin registration."""
from django.contrib import admin
from .models import Team, Venue, Match, MatchScorecard


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'country', 'is_international']
    search_fields = ['name', 'country']
    list_filter = ['is_international']


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'country', 'pitch_type']
    search_fields = ['name', 'city']
    list_filter = ['pitch_type']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['name', 'team1', 'team2', 'format', 'category', 'status', 'match_date']
    list_filter = ['status', 'format', 'category']
    search_fields = ['name', 'team1__name', 'team2__name']
    raw_id_fields = ['team1', 'team2', 'venue', 'winner', 'toss_winner']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'match_date'


@admin.register(MatchScorecard)
class MatchScorecardAdmin(admin.ModelAdmin):
    list_display = ['match', 'innings_number', 'batting_team', 'total_runs', 'total_wickets', 'total_overs']
    raw_id_fields = ['match', 'batting_team']
