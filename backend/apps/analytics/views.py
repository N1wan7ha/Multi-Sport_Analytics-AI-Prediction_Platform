from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from apps.matches.models import Match
from apps.players.models import Player

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    def get(self, request):
        return Response({
            'total_matches': Match.objects.count(),
            'live_matches': Match.objects.filter(status='live').count(),
            'upcoming_matches': Match.objects.filter(status='upcoming').count(),
            'total_players': Player.objects.count(),
        })

class TeamAnalyticsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    def get(self, request, team_name):
        # TODO Phase 4: add win/loss rates, form streaks
        return Response({'team': team_name, 'status': 'coming_soon'})

class PlayerAnalyticsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    def get(self, request, player_id):
        # TODO Phase 4: add career stats trends
        return Response({'player_id': player_id, 'status': 'coming_soon'})
