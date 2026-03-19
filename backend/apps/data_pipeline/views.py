from django.core.cache import cache
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView


class PipelineStatusView(APIView):
    """Expose pipeline sync counters and last-run timestamps from cache."""

    permission_classes = [IsAuthenticatedOrReadOnly]

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
            payload['pipeline'][name] = {
                'last_sync_count': cache.get(f"{prefix}:last_sync_count"),
                'last_sync_at': cache.get(f"{prefix}:last_sync_at"),
            }

        return Response(payload)
