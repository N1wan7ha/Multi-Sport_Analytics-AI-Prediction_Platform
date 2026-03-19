"""Players admin registration."""
from django.contrib import admin
from .models import Player, PlayerMatchStats


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'role', 'batting_style', 'bowling_style', 'team']
    list_filter = ['role', 'country']
    search_fields = ['name', 'full_name', 'country']
    raw_id_fields = ['team']


@admin.register(PlayerMatchStats)
class PlayerMatchStatsAdmin(admin.ModelAdmin):
    list_display = ['player', 'match', 'innings_number', 'runs_scored', 'balls_faced', 'wickets_taken']
    raw_id_fields = ['player', 'match']
    list_filter = ['innings_number']
