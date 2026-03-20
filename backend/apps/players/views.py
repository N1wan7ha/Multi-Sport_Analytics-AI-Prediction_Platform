from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Player, PlayerMatchStats
from rest_framework import serializers


class RecentPlayerMatchStatsSerializer(serializers.ModelSerializer):
    match_id = serializers.IntegerField(source='match.id', read_only=True)
    match_name = serializers.CharField(source='match.name', read_only=True)
    match_date = serializers.DateField(source='match.match_date', read_only=True)

    class Meta:
        model = PlayerMatchStats
        fields = [
            'match_id', 'match_name', 'match_date', 'innings_number',
            'runs_scored', 'balls_faced', 'fours', 'sixes', 'strike_rate',
            'overs_bowled', 'runs_conceded', 'wickets_taken', 'economy',
        ]


class PlayerSerializer(serializers.ModelSerializer):
    recent_stats = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = [
            'id', 'cricapi_id', 'name', 'full_name', 'country', 'date_of_birth',
            'batting_style', 'bowling_style', 'role', 'team', 'image_url',
            'raw_data', 'created_at', 'updated_at', 'recent_stats',
        ]

    def get_recent_stats(self, obj):
        stats_qs = obj.match_stats.select_related('match').order_by('-match__match_date', '-id')[:10]
        return RecentPlayerMatchStatsSerializer(stats_qs, many=True).data


class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Player.objects.select_related('team').prefetch_related('match_stats__match').all().order_by('name')
    serializer_class = PlayerSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'full_name', 'country', 'team__name']
