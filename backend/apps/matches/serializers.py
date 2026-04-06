"""Matches serializers."""
from rest_framework import serializers
from .models import Match, Team, Venue, MatchScorecard


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'short_name', 'logo_url', 'country', 'is_international']


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ['id', 'name', 'city', 'country', 'pitch_type']


class MatchScorecardSerializer(serializers.ModelSerializer):
    batting_team = TeamSerializer(read_only=True)
    
    class Meta:
        model = MatchScorecard
        fields = ['innings_number', 'batting_team', 'total_runs', 'total_wickets',
                  'total_overs', 'run_rate', 'batting_data', 'bowling_data']


class MatchSerializer(serializers.ModelSerializer):
    team1 = TeamSerializer(read_only=True)
    team2 = TeamSerializer(read_only=True)
    venue = VenueSerializer(read_only=True)
    scorecards = MatchScorecardSerializer(many=True, read_only=True)

    class Meta:
        model = Match
        fields = [
            'id', 'name', 'cricapi_id', 'cricbuzz_id',
            'team1', 'team2', 'venue',
            'format', 'category', 'status',
            'match_date', 'result_text',
            'scorecards', 'created_at', 'updated_at',
        ]
