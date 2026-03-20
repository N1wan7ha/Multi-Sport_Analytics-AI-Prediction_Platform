from django.db.models import Q, Count, Sum, Avg
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from apps.matches.models import Match, Team
from apps.players.models import Player, PlayerMatchStats

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
        team = get_object_or_404(Team, name__iexact=team_name)
        all_matches = Match.objects.filter(Q(team1=team) | Q(team2=team))
        completed = all_matches.filter(status='complete')
        wins = completed.filter(winner=team).count()
        losses = completed.exclude(winner=team).exclude(winner__isnull=True).count()
        ties_or_nr = completed.filter(winner__isnull=True).count()

        total_completed = completed.count()
        win_rate = round((wins / total_completed) * 100, 2) if total_completed else 0.0

        recent_results = []
        for match in completed.order_by('-match_date', '-id')[:5]:
            if match.winner_id == team.id:
                outcome = 'W'
            elif match.winner_id is None:
                outcome = 'N'
            else:
                outcome = 'L'
            recent_results.append({
                'match_id': match.id,
                'match_name': match.name,
                'match_date': match.match_date,
                'outcome': outcome,
            })

        by_format_rows = completed.values('format').annotate(total=Count('id')).order_by('format')
        by_format = {row['format']: row['total'] for row in by_format_rows}

        return Response({
            'team': team.name,
            'total_matches': all_matches.count(),
            'completed_matches': total_completed,
            'wins': wins,
            'losses': losses,
            'ties_or_no_result': ties_or_nr,
            'win_rate_percent': win_rate,
            'recent_form': recent_results,
            'by_format': by_format,
        })


class PlayerAnalyticsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, player_id):
        player = get_object_or_404(Player, pk=player_id)
        stats = PlayerMatchStats.objects.filter(player=player).select_related('match').order_by('-match__match_date', '-id')

        agg = stats.aggregate(
            matches=Count('id'),
            total_runs=Sum('runs_scored'),
            total_wickets=Sum('wickets_taken'),
            batting_avg=Avg('runs_scored'),
            strike_rate_avg=Avg('strike_rate'),
            economy_avg=Avg('economy'),
        )

        recent = []
        for row in stats[:10]:
            recent.append({
                'match_id': row.match_id,
                'match_name': row.match.name,
                'match_date': row.match.match_date,
                'runs_scored': row.runs_scored,
                'wickets_taken': row.wickets_taken,
                'strike_rate': row.strike_rate,
                'economy': row.economy,
            })

        return Response({
            'player_id': player.id,
            'player_name': player.name,
            'matches': agg['matches'] or 0,
            'total_runs': agg['total_runs'] or 0,
            'total_wickets': agg['total_wickets'] or 0,
            'batting_average': round(agg['batting_avg'] or 0.0, 2),
            'average_strike_rate': round(agg['strike_rate_avg'] or 0.0, 2),
            'average_economy': round(agg['economy_avg'] or 0.0, 2),
            'recent_performances': recent,
        })
