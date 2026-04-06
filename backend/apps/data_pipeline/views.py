from django.core.cache import cache
from apps.matches.models import Match
from apps.players.models import PlayerMatchStats
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView


class PipelineStatusView(APIView):
    """Expose pipeline sync counters and last-run timestamps from cache."""

    permission_classes = [IsAuthenticatedOrReadOnly]

    @staticmethod
    def _fallback_for(name: str):
        if name == 'current_matches':
            count = Match.objects.exclude(status='complete').count()
            last = Match.objects.exclude(status='complete').order_by('-updated_at').values_list('updated_at', flat=True).first()
            return count, (last.isoformat() if last else None)

        if name == 'live_matches':
            count = Match.objects.filter(status='live').count()
            last = Match.objects.filter(status='live').order_by('-updated_at').values_list('updated_at', flat=True).first()
            return count, (last.isoformat() if last else None)

        if name == 'completed_matches':
            count = Match.objects.filter(status='complete').count()
            last = Match.objects.filter(status='complete').order_by('-updated_at').values_list('updated_at', flat=True).first()
            return count, (last.isoformat() if last else None)

        if name == 'player_stats':
            count = PlayerMatchStats.objects.count()
            return count, None

        if name == 'unified_matches':
            count = Match.objects.count()
            last = Match.objects.order_by('-updated_at').values_list('updated_at', flat=True).first()
            return count, (last.isoformat() if last else None)

        return None, None

    def get(self, request):
        keys = {
            'current_matches': 'pipeline:current_matches',
            'live_matches': 'pipeline:live_matches',
            'completed_matches': 'pipeline:completed_matches',
            'player_stats': 'pipeline:player_stats',
            'unified_matches': 'pipeline:unified_matches',
        }

        payload = {'pipeline': {}}
        for name, prefix in keys.items():
            count = cache.get(f"{prefix}:last_sync_count")
            last_sync_at = cache.get(f"{prefix}:last_sync_at")
            if count is None:
                count, fallback_last_sync_at = self._fallback_for(name)
                if last_sync_at is None:
                    last_sync_at = fallback_last_sync_at

            payload['pipeline'][name] = {
                'last_sync_count': count,
                'last_sync_at': last_sync_at,
            }

        return Response(payload)


class ManualMatchSyncView(APIView):
    """Trigger an immediate background sync for a specific match's scorecard/live data."""

    def post(self, request):
        match_id = request.data.get('match_id')
        if not match_id:
            return Response({'error': 'match_id is required'}, status=400)

        match = Match.objects.filter(id=match_id).first()
        if not match:
            return Response({'error': 'Match not found'}, status=404)

        # Trigger sync_player_stats task
        from .tasks import sync_player_stats
        
        # Determine the source ID to use
        source_id = match.cricapi_id or match.cricbuzz_id
        if not source_id:
            return Response({'error': 'Match has no provider ID for syncing live data'}, status=400)

        # We run it as a background task
        sync_player_stats.delay(match_id=source_id)
        
        return Response({'status': 'Sync triggered', 'source_id': source_id})


class GithubSyncView(APIView):
    """Trigger a sync from a public GitHub JSON feed."""

    def post(self, request):
        json_url = request.data.get('json_url')
        if not json_url:
            return Response({'error': 'json_url is required'}, status=400)

        from .tasks import sync_from_github_data
        sync_from_github_data.delay(json_url=json_url)
        
        return Response({'status': 'GitHub sync triggered', 'url': json_url})
